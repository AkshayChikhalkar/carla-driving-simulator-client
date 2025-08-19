import os
import time
from carla_simulator.utils.logging import Logger
from typing import Dict, Optional, Tuple, List
import threading


class CarlaPoolError(Exception):
    pass


class CarlaContainerManager:
    """
    Manages lifecycle of per-tenant CARLA server containers.
    Strategy:
    - One container per tenant (on-demand)
    - Attach to a shared Docker network so backend can reach by container name
    - If a container is already running for tenant, reuse it
    - Optionally set GPU runtime if requested
    """

    def __init__(self) -> None:
        self._logger = Logger()
        self._tenant_to_container: Dict[int, str] = {}
        self._tenant_last_used: Dict[int, float] = {}
        # Use reentrant lock: static acquire() may call methods that also acquire the same lock
        self._lock = threading.RLock()
        self._docker = None
        self._image = os.getenv("CARLA_IMAGE", "carlasim/carla:0.10.0")
        self._network = os.getenv("CARLA_NETWORK", "carla-network")
        self._use_gpu = os.getenv("CARLA_USE_GPU", "true").lower() == "true"
        self._container_prefix = os.getenv("CARLA_CONTAINER_PREFIX", "carla-tenant-")
        self._container_command = os.getenv(
            "CARLA_COMMAND",
            "./CarlaUnreal.sh -RenderOffScreen -quality-level=High -fps=60 -ResX=1920 -ResY=1080 -opengl",
        )
        # Pool mode: docker | static
        self._mode = os.getenv("CARLA_POOL_MODE", "docker").lower()
        # Static endpoints in form host:port,host:port
        self._static_endpoints: List[Tuple[str, int]] = []
        self._static_in_use: Dict[Tuple[str, int], Optional[int]] = {}
        if self._mode == "static":
            eps = os.getenv("CARLA_STATIC_ENDPOINTS", "").strip()
            for item in [e for e in eps.split(",") if e]:
                host, port_s = item.split(":")
                ep = (host.strip(), int(port_s))
                self._static_endpoints.append(ep)
                self._static_in_use[ep] = None
        # Capacity limits
        self._max_users = int(os.getenv("CARLA_MAX_USERS", "10"))
        self._idle_stop_seconds = int(os.getenv("CARLA_IDLE_STOP_SECONDS", "600"))  # 10 min
        self._keep_warm = int(os.getenv("CARLA_KEEP_WARM", "1"))

    def _client(self):
        if self._docker is None:
            import docker  # lazy import

            self._docker = docker.from_env()
        return self._docker

    def _ensure_network(self) -> None:
        client = self._client()
        try:
            client.networks.get(self._network)
        except Exception:
            # Try create if missing
            client.networks.create(self._network, driver="bridge")

    def _container_name(self, tenant_id: int) -> str:
        return f"{self._container_prefix}{tenant_id}"

    def acquire(self, tenant_id: int, timeout_seconds: int = 120) -> Tuple[str, int]:
        """
        Acquire a CARLA endpoint for this tenant and return (host, port).
        - docker mode: ensure container exists and is running; host is container name on shared network, port 2000
        - static mode: reserve an available endpoint from the configured list
        """
        # Short-circuit if already assigned
        if self._mode == "static":
            # Check if this tenant already holds an endpoint
            with self._lock:
                for ep, used_by in self._static_in_use.items():
                    if used_by == tenant_id:
                        self._tenant_last_used[tenant_id] = time.time()
                        self._logger.info(f"CARLA pool: tenant {tenant_id} reusing endpoint {ep[0]}:{ep[1]}")
                        return ep
                # Enforce max users
                if self.in_use_count() >= self._max_users:
                    raise CarlaPoolError("No capacity available")
                # Find a free endpoint
                for ep, used_by in self._static_in_use.items():
                    if used_by is None:
                        self._static_in_use[ep] = tenant_id
                        self._tenant_last_used[tenant_id] = time.time()
                        self._logger.info(f"CARLA pool: tenant {tenant_id} assigned endpoint {ep[0]}:{ep[1]}")
                        return ep
            raise CarlaPoolError("No static CARLA endpoints available")

        name = self._container_name(tenant_id)
        client = self._client()
        self._ensure_network()

        # Fast path: already tracked
        tracked = None
        with self._lock:
            tracked = self._tenant_to_container.get(tenant_id)
        if tracked:
            try:
                ctr = client.containers.get(name)
                if ctr.status != "running":
                    ctr.start()
            except Exception:
                # Fallthrough to recreation
                with self._lock:
                    self._tenant_to_container.pop(tenant_id, None)
            else:
                with self._lock:
                    self._tenant_last_used[tenant_id] = time.time()
                self._logger.info(f"CARLA pool: tenant {tenant_id} using container {name}:2000")
                return name, 2000

        # Check if container exists by name
        try:
            ctr = client.containers.get(name)
            if ctr.status != "running":
                ctr.start()
        except Exception:
            # Create a new container
            run_kwargs = dict(
                image=self._image,
                name=name,
                detach=True,
                command=self._container_command,
                shm_size="32g",
                environment={
                    "NVIDIA_VISIBLE_DEVICES": "all",
                    "NVIDIA_DRIVER_CAPABILITIES": "compute,utility,graphics",
                }
                if self._use_gpu
                else {},
            )

            # Network attach
            run_kwargs["network"] = self._network

            # GPU runtime
            if self._use_gpu:
                try:
                    run_kwargs["runtime"] = "nvidia"
                except Exception:
                    pass

            # Launch
            # Enforce max capacity
            if self.running_container_count() >= self._max_users:
                raise CarlaPoolError("No capacity available")
            ctr = client.containers.run(**run_kwargs)

        # Attach to network (idempotent)
        try:
            net = client.networks.get(self._network)
            net.connect(ctr, aliases=[name])
        except Exception:
            pass

        # Wait for readiness: poll for process up to timeout
        start = time.time()
        while time.time() - start < timeout_seconds:
            ctr.reload()
            if ctr.status == "running":
                # Optionally check logs for readiness; keep simple
                with self._lock:
                    self._tenant_to_container[tenant_id] = ctr.id
                    self._tenant_last_used[tenant_id] = time.time()
                self._logger.info(f"CARLA pool: tenant {tenant_id} using container {name}:2000")
                return name, 2000
            time.sleep(2)

        raise CarlaPoolError("Timed out waiting for CARLA container to be ready")

    def release(self, tenant_id: int, stop: bool = False) -> None:
        """Release the tenant's CARLA resource.
        - docker mode: optionally stop container; otherwise leave running
        - static mode: free the endpoint
        """
        with self._lock:
            self._tenant_last_used[tenant_id] = time.time()
        if self._mode == "static":
            with self._lock:
                for ep, used_by in list(self._static_in_use.items()):
                    if used_by == tenant_id:
                        self._static_in_use[ep] = None
                        self._logger.info(f"CARLA pool: tenant {tenant_id} released endpoint {ep[0]}:{ep[1]}")
                        break
            return
        name = self._container_name(tenant_id)
        try:
            ctr = self._client().containers.get(name)
            if stop:
                ctr.stop(timeout=20)
        except Exception:
            pass
        finally:
            with self._lock:
                self._tenant_to_container.pop(tenant_id, None)
            self._logger.info(f"CARLA pool: tenant {tenant_id} released container {name}:2000")

    # ---- Pool status and housekeeping ----
    def in_use_count(self) -> int:
        if self._mode == "static":
            with self._lock:
                return sum(1 for v in self._static_in_use.values() if v is not None)
        # Running containers associated with tenants
        with self._lock:
            return len(self._tenant_to_container)

    def running_container_count(self) -> int:
        if self._mode == "static":
            return len(self._static_endpoints)
        try:
            return len(self._client().containers.list(filters={"ancestor": self._image, "status": "running"}))
        except Exception:
            return len(self._tenant_to_container)

    def status(self) -> Dict[str, object]:
        if self._mode == "static":
            return {
                "mode": self._mode,
                "capacity": len(self._static_endpoints),
                "in_use": self.in_use_count(),
                "endpoints": [
                    {
                        "host": ep[0],
                        "port": ep[1],
                        "used_by": self._static_in_use[ep],
                    }
                    for ep in self._static_endpoints
                ],
            }
        # docker mode
        with self._lock:
            tenants = [
                {"tenant_id": tid, "container": cid, "last_used": self._tenant_last_used.get(tid)}
                for tid, cid in self._tenant_to_container.items()
            ]
        return {
            "mode": self._mode,
            "image": self._image,
            "network": self._network,
            "in_use": self.in_use_count(),
            "running_total": self.running_container_count(),
            "tenants": tenants,
        }

    def housekeeping(self) -> None:
        """Stop idle containers beyond keep-warm count (docker mode only)."""
        if self._mode != "docker":
            return
        client = self._client()
        now = time.time()
        # Determine idle candidates
        # Keep at least self._keep_warm running; stop oldest idle first
        # Build list of (tenant_id, last_used, container)
        entries = []
        with self._lock:
            items_snapshot = list(self._tenant_to_container.items())
            last_used_snapshot = dict(self._tenant_last_used)
        for tid, cid in items_snapshot:
            last = last_used_snapshot.get(tid, 0)
            try:
                ctr = client.containers.get(self._container_name(tid))
            except Exception:
                continue
            entries.append((tid, last, ctr))
        # Sort by last used ascending
        entries.sort(key=lambda x: x[1])
        running = self.running_container_count()
        for tid, last, ctr in entries:
            if running <= self._keep_warm:
                break
            if last and now - last >= self._idle_stop_seconds:
                try:
                    ctr.stop(timeout=20)
                    running -= 1
                except Exception:
                    pass
                finally:
                    with self._lock:
                        self._tenant_to_container.pop(tid, None)


