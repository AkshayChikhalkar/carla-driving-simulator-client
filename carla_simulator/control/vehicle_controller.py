from typing import Dict, Any
import carla
from carla_simulator.core.interfaces import IVehicleController
import math


class VehicleController(IVehicleController):
    """Controller for vehicle movement and behavior"""

    def __init__(self, vehicle: carla.Vehicle):
        """Initialize controller with vehicle instance"""
        self._vehicle = vehicle
        self._target = None

    def get_vehicle(self) -> carla.Vehicle:
        """Get the controlled vehicle instance"""
        return self._vehicle

    def get_control(self, vehicle_state: Dict[str, Any]) -> carla.VehicleControl:
        """Get control commands based on vehicle state"""
        control = carla.VehicleControl()

        # If we have a target, calculate control based on distance and heading
        if self._target:
            # Get current location and target location
            current_loc = vehicle_state["location"]
            target_loc = self._target

            # Calculate distance to target
            distance = current_loc.distance(target_loc)

            # Calculate heading to target
            dx = target_loc.x - current_loc.x
            dy = target_loc.y - current_loc.y
            target_heading = math.degrees(math.atan2(dy, dx))

            # Get current vehicle heading
            vehicle_heading = vehicle_state["transform"].rotation.yaw

            # Calculate heading difference
            heading_diff = (target_heading - vehicle_heading + 180) % 360 - 180

            # Set steering based on heading difference
            control.steer = max(-1.0, min(1.0, heading_diff / 45.0))

            # Set throttle based on distance
            if distance > 10.0:
                control.throttle = 0.75
            elif distance > 5.0:
                control.throttle = 0.5
            else:
                control.throttle = 0.25

            # Apply brakes if we're too close
            if distance < 2.0:
                control.brake = 1.0
                control.throttle = 0.0

        return control

    def set_target(self, target: carla.Location) -> None:
        """Set the target location for the vehicle"""
        self._target = target
