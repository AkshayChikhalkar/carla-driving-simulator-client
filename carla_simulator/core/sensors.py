"""
Sensor system using the observer pattern.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable
import carla
import weakref
import math
import numpy as np
from dataclasses import dataclass
from ..utils.config import SensorConfig
from ..utils.logging import Logger
import time

# Get logger instance
logger = Logger()


@dataclass
class SensorData:
    """Base class for sensor data"""

    frame: int
    timestamp: float
    transform: carla.Transform


@dataclass
class CollisionData(SensorData):
    """Data from collision sensor"""

    other_actor: carla.Actor
    impulse: carla.Vector3D
    intensity: float


@dataclass
class CameraData(SensorData):
    """Data from camera sensor"""

    image: np.ndarray
    width: int
    height: int


@dataclass
class GNSSData(SensorData):
    """Data from GNSS sensor"""

    latitude: float
    longitude: float
    altitude: float


class SensorObserver(ABC):
    """Abstract base class for sensor observers"""

    @abstractmethod
    def on_sensor_data(self, data: SensorData) -> None:
        """Handle new sensor data"""
        pass


class SensorSubject(ABC):
    """Abstract base class for sensor subjects"""

    def __init__(self):
        self._observers: List[SensorObserver] = []

    def attach(self, observer: SensorObserver) -> None:
        """Attach an observer"""
        self._observers.append(observer)

    def detach(self, observer: SensorObserver) -> None:
        """Detach an observer"""
        self._observers.remove(observer)

    def notify(self, data: SensorData) -> None:
        """Notify all observers of new data"""
        for observer in self._observers:
            observer.on_sensor_data(data)

    def detach_all(self) -> None:
        """Detach all observers"""
        self._observers.clear()


class CollisionSensor(SensorSubject):
    """Collision detection sensor"""

    def __init__(self, vehicle: carla.Vehicle, config: Dict[str, Any], world_manager=None):
        super().__init__()
        self.vehicle = vehicle
        self.config = config
        self.world_manager = world_manager
        world = self.vehicle.get_world()

        # Create collision sensor
        bp = world.get_blueprint_library().find("sensor.other.collision")
        self.sensor = world.spawn_actor(bp, carla.Transform(), attach_to=vehicle)
        
        # Track the sensor actor if world manager is available
        if self.world_manager and hasattr(self.world_manager, 'track_sensor_actor'):
            self.world_manager.track_sensor_actor(self.sensor)

        # Weak reference to avoid circular reference
        weak_self = weakref.ref(self)
        self.sensor.listen(
            lambda event: CollisionSensor._on_collision(weak_self, event)
        )

    @staticmethod
    def _on_collision(
        weak_self: weakref.ReferenceType, event: carla.CollisionEvent
    ) -> None:
        """Collision event callback"""
        self = weak_self()
        if not self:
            return

        # Calculate collision intensity
        impulse = event.normal_impulse
        intensity = math.sqrt(impulse.x**2 + impulse.y**2 + impulse.z**2)

        # Create collision data
        data = CollisionData(
            frame=event.frame,
            timestamp=event.timestamp,
            transform=event.transform,
            other_actor=event.other_actor,
            impulse=impulse,
            intensity=intensity,
        )

        # Notify observers
        self.notify(data)

    def destroy(self) -> None:
        """Clean up the sensor"""
        if self.sensor is not None:
            self.sensor.destroy()


class CameraSensor(SensorSubject):
    """Camera sensor"""

    def __init__(self, vehicle: carla.Vehicle, config: Dict[str, Any], world_manager=None):
        super().__init__()
        self.vehicle = vehicle
        self.config = config
        self.world_manager = world_manager
        world = self.vehicle.get_world()

        # Create camera sensor
        bp = world.get_blueprint_library().find("sensor.camera.rgb")
        if not bp:
            return

        # Defaults; will be overridden by advanced attributes if present
        bp.set_attribute("image_size_x", str(1280))
        bp.set_attribute("image_size_y", str(720))
        bp.set_attribute("fov", str(90))

        # Apply advanced sensor attributes if provided in configuration
        try:
            if world_manager and hasattr(world_manager, 'app') and hasattr(world_manager.app, '_config'):
                adv = getattr(world_manager.app._config, 'advanced', None) or {}
                attrs = (adv.get('sensor', {}) or {}).get('attributes', {})
                for k, v in attrs.items():
                    try:
                        bp.set_attribute(str(k), str(v))
                    except Exception:
                        pass
        except Exception:
            pass

        spawn_point = carla.Transform(
            carla.Location(x=-6.0, y=0.0, z=3.0), carla.Rotation(pitch=-15)
        )

        self.sensor = world.spawn_actor(bp, spawn_point, attach_to=vehicle)
        
        # Track the sensor actor if world manager is available
        if self.world_manager and hasattr(self.world_manager, 'track_sensor_actor'):
            self.world_manager.track_sensor_actor(self.sensor)

        if self.sensor is not None:
            weak_self = weakref.ref(self)
            self.sensor.listen(lambda image: CameraSensor._on_image(weak_self, image))

    @staticmethod
    def _on_image(weak_self: weakref.ReferenceType, image: carla.Image) -> None:
        self = weak_self()
        if not self:
            return

        try:
            array = np.frombuffer(image.raw_data, dtype=np.dtype("uint8"))
            array = np.reshape(array, (image.height, image.width, 4))
            array = array[:, :, :3]
            data = CameraData(
                frame=image.frame,
                timestamp=image.timestamp,
                transform=image.transform,
                image=array,
                width=image.width,
                height=image.height,
            )
            self.notify(data)
        except Exception:
            pass

    def destroy(self) -> None:
        if self.sensor is not None:
            self.sensor.destroy()


class GNSSSensor(SensorSubject):
    """GNSS (GPS) sensor"""

    def __init__(self, vehicle: carla.Vehicle, config: Dict[str, Any], world_manager=None):
        super().__init__()
        self.vehicle = vehicle
        self.config = config
        self.world_manager = world_manager
        world = self.vehicle.get_world()

        # Create GNSS sensor
        bp = world.get_blueprint_library().find("sensor.other.gnss")
        self.sensor = world.spawn_actor(
            bp, carla.Transform(carla.Location(x=0.0, z=0.0)), attach_to=vehicle
        )
        
        # Track the sensor actor if world manager is available
        if self.world_manager and hasattr(self.world_manager, 'track_sensor_actor'):
            self.world_manager.track_sensor_actor(self.sensor)

        # Weak reference to avoid circular reference
        weak_self = weakref.ref(self)
        self.sensor.listen(lambda event: GNSSSensor._on_gnss_data(weak_self, event))

    @staticmethod
    def _on_gnss_data(
        weak_self: weakref.ReferenceType, event: carla.GnssMeasurement
    ) -> None:
        """GNSS data callback"""
        self = weak_self()
        if not self:
            return

        # Create GNSS data
        data = GNSSData(
            frame=event.frame,
            timestamp=event.timestamp,
            transform=event.transform,
            latitude=event.latitude,
            longitude=event.longitude,
            altitude=event.altitude,
        )

        # Notify observers
        self.notify(data)

    def destroy(self) -> None:
        """Clean up the sensor"""
        if self.sensor is not None:
            self.sensor.destroy()


class SensorManager:
    """Manages all vehicle sensors"""

    def __init__(self, vehicle: carla.Vehicle, config: SensorConfig, world_manager=None):
        self.vehicle = vehicle
        self.config = config
        self.world_manager = world_manager
        self.sensors: Dict[str, SensorSubject] = {}
        if config.collision.enabled:
            self.sensors["collision"] = CollisionSensor(vehicle, {"enabled": True}, world_manager)
        if config.camera.enabled:
            self.sensors["camera"] = CameraSensor(vehicle, {"enabled": True}, world_manager)
        if config.gnss.enabled:
            self.sensors["gnss"] = GNSSSensor(vehicle, {"enabled": True}, world_manager)

    def add_observer(self, sensor_type: str, observer: SensorObserver) -> None:
        if sensor_type in self.sensors:
            self.sensors[sensor_type].attach(observer)

    def remove_observer(self, sensor_type: str, observer: SensorObserver) -> None:
        if sensor_type in self.sensors:
            self.sensors[sensor_type].detach(observer)

    def get_sensor(self, sensor_type: str) -> Optional[SensorSubject]:
        return self.sensors.get(sensor_type)

    def get_sensor_data(self) -> Dict[str, Any]:
        return {}

    def cleanup(self) -> None:
        """Clean up all sensors"""
        try:
            logger.debug("[SensorManager] Starting sensor cleanup...")

            # First detach all observers
            for sensor in list(self.sensors.values()):
                if sensor:
                    sensor.detach_all()

            # Then destroy each sensor
            for sensor_type, sensor in list(self.sensors.items()):
                try:
                    # Attempt to stop sensor stream if supported to avoid callbacks during teardown
                    if hasattr(sensor, 'sensor') and sensor.sensor is not None:
                        try:
                            if hasattr(sensor.sensor, 'stop'):
                                sensor.sensor.stop()
                        except Exception:
                            pass
                    if hasattr(sensor, 'sensor') and sensor.sensor is not None and getattr(sensor.sensor, 'is_alive', True):
                        try:
                            logger.debug(f"[SensorManager] Destroying sensor: {sensor_type}")
                            sensor.destroy()
                            time.sleep(0.05)  # Small delay between sensor destruction
                        except Exception as e:
                            logger.error(f"[SensorManager] Error destroying sensor {sensor_type}: {str(e)}")
                except Exception as e:
                    logger.error(f"[SensorManager] Error during sensor '{sensor_type}' teardown: {str(e)}")

            # Clear the sensors dictionary
            self.sensors.clear()

            logger.debug("[SensorManager] Sensor cleanup completed")

        except Exception as e:
            logger.error(f"[SensorManager] Error during sensor cleanup: {str(e)}")
            raise
