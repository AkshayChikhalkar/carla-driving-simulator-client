"""
Vehicle management system with state tracking.
"""

import carla
import math
import numpy as np
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple, Union
from ..control.controller import VehicleControl


@dataclass
class VehicleState:
    """Vehicle state information"""

    speed: float  # Current speed in m/s
    position: Tuple[float, float, float]  # (x, y, z) in world coordinates
    rotation: Tuple[float, float, float]  # (pitch, yaw, roll) in degrees
    acceleration: float  # Current acceleration in m/s²
    angular_velocity: float  # Angular velocity in rad/s
    collision_intensity: float  # Intensity of last collision
    distance_to_target: float  # Distance to target in meters
    heading_to_target: float  # Heading to target in degrees
    heading_difference: float  # Difference between current and target heading

    @property
    def speed_kmh(self) -> float:
        """Get speed in kilometers per hour"""
        return self.speed * 3.6

    @property
    def heading(self) -> float:
        """Get vehicle heading (yaw angle) in degrees"""
        return self.rotation[1]  # yaw angle

    @property
    def pitch(self) -> float:
        """Get vehicle pitch in degrees"""
        return self.rotation[0]

    @property
    def roll(self) -> float:
        """Get vehicle roll in degrees"""
        return self.rotation[2]


class VehicleManager:
    """Manages vehicle state and operations"""

    def __init__(self, world: carla.World, config: Union[str, Dict[str, Any]]):
        """Initialize vehicle manager"""
        self.world = world
        self.config = {"vehicle_model": config} if isinstance(config, str) else config
        self.vehicle: Optional[carla.Vehicle] = None
        self._state = VehicleState(
            speed=0.0,
            position=(0.0, 0.0, 0.0),
            rotation=(0.0, 0.0, 0.0),
            acceleration=0.0,
            angular_velocity=0.0,
            collision_intensity=0.0,
            distance_to_target=float("inf"),
            heading_to_target=0.0,
            heading_difference=0.0,
        )
        self._spawn_point: Optional[carla.Transform] = None
        self._target_point: Optional[carla.Location] = None

    def set_target(self, location: carla.Location) -> None:
        """Set target location for the vehicle"""
        self._target_point = location

    def apply_control(self, control: VehicleControl) -> None:
        """Apply control input to vehicle"""
        if self.vehicle is None:
            raise RuntimeError("Vehicle not spawned")

        # Convert our control format to CARLA control
        carla_control = carla.VehicleControl(
            throttle=float(control.throttle),
            steer=float(control.steer),
            brake=float(control.brake),
            hand_brake=bool(control.hand_brake),
            reverse=bool(control.reverse),
            manual_gear_shift=bool(control.manual_gear_shift),
            gear=int(control.gear),
        )

        self.vehicle.apply_control(carla_control)

    def update_state(self) -> None:
        """Update vehicle state information"""
        if self.vehicle is None:
            return

        # Get vehicle transform and velocity
        transform = self.vehicle.get_transform()
        velocity = self.vehicle.get_velocity()
        angular_velocity = self.vehicle.get_angular_velocity()

        # Calculate speed and acceleration
        speed = math.sqrt(velocity.x**2 + velocity.y**2 + velocity.z**2)
        acceleration = self.vehicle.get_acceleration()
        acceleration_magnitude = math.sqrt(
            acceleration.x**2 + acceleration.y**2 + acceleration.z**2
        )

        # Calculate angular velocity magnitude
        angular_velocity_magnitude = math.sqrt(
            angular_velocity.x**2 + angular_velocity.y**2 + angular_velocity.z**2
        )

        # Update target-related information if target exists
        distance_to_target = float("inf")
        heading_to_target = 0.0
        heading_difference = 0.0

        if self._target_point is not None:
            # Calculate distance to target
            distance_to_target = math.sqrt(
                (transform.location.x - self._target_point.x) ** 2
                + (transform.location.y - self._target_point.y) ** 2
                + (transform.location.z - self._target_point.z) ** 2
            )

            # Calculate heading to target
            heading_to_target = math.degrees(
                math.atan2(
                    self._target_point.y - transform.location.y,
                    self._target_point.x - transform.location.x,
                )
            )

            # Calculate heading difference
            heading_difference = heading_to_target - transform.rotation.yaw
            heading_difference = (
                heading_difference + 180
            ) % 360 - 180  # Normalize to [-180, 180]

        # Update state
        self._state = VehicleState(
            speed=speed,
            position=(transform.location.x, transform.location.y, transform.location.z),
            rotation=(
                transform.rotation.pitch,
                transform.rotation.yaw,
                transform.rotation.roll,
            ),
            acceleration=acceleration_magnitude,
            angular_velocity=angular_velocity_magnitude,
            collision_intensity=self._state.collision_intensity,  # Maintained by collision sensor
            distance_to_target=distance_to_target,
            heading_to_target=heading_to_target,
            heading_difference=heading_difference,
        )

    @property
    def state(self) -> VehicleState:
        """Get current vehicle state"""
        return self._state

    def update_collision_intensity(self, intensity: float) -> None:
        """Update collision intensity from sensor"""
        self._state.collision_intensity = intensity

    def reset(self) -> None:
        """Reset vehicle to initial state"""
        if self.vehicle is not None:
            self.vehicle.set_transform(self._spawn_point)
            self.vehicle.set_velocity(carla.Vector3D())
            self.vehicle.set_angular_velocity(carla.Vector3D())
            self.vehicle.set_target_velocity(carla.Vector3D())

            # Reset state
            self._state = VehicleState(
                speed=0.0,
                position=(
                    self._spawn_point.location.x,
                    self._spawn_point.location.y,
                    self._spawn_point.location.z,
                ),
                rotation=(
                    self._spawn_point.rotation.pitch,
                    self._spawn_point.rotation.yaw,
                    self._spawn_point.rotation.roll,
                ),
                acceleration=0.0,
                angular_velocity=0.0,
                collision_intensity=0.0,
                distance_to_target=float("inf"),
                heading_to_target=0.0,
                heading_difference=0.0,
            )

    def destroy(self) -> None:
        """Clean up vehicle"""
        if self.vehicle is not None:
            self.vehicle.destroy()
            self.vehicle = None
