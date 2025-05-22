"""
Main application module for the CARLA Driving Simulator.
Coordinates all components and manages the simulation loop.
"""

import carla
import time
import sys
import os
import pygame
import logging
import datetime
import math
import numpy as np
from typing import Dict, Any, Optional, List
from pathlib import Path
import random
from enum import Enum, auto

# Add the project root directory to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.utils.config import load_config, Config
from src.utils.logging import SimulationLogger, SimulationData
from src.core.vehicle import VehicleManager
from src.core.world_manager import WorldManager
from src.core.sensors import SensorManager, SensorObserver, CollisionData, CameraData
from src.visualization.display_manager import DisplayManager, VehicleState as DisplayVehicleState
from src.control.controller import VehicleController, KeyboardController, GamepadController, AutopilotController

class ScenarioType(Enum):
    """Types of available scenarios"""
    EMERGENCY_BRAKE = auto()
    VEHICLE_CUTTING = auto()
    FOLLOW_ROUTE = auto()
    PEDESTRIAN_CROSSING = auto()
    AVOID_OBSTACLE = auto()

class Scenario:
    """Base class for all scenarios"""
    def __init__(self, world_manager, vehicle_manager):
        self.world_manager = world_manager
        self.vehicle_manager = vehicle_manager
        self.is_completed = False
        self.success = False
        self.start_time = None
        self.completion_time = None

    def setup(self):
        """Setup the scenario"""
        pass

    def update(self):
        """Update scenario state"""
        pass

    def cleanup(self):
        """Clean up scenario resources"""
        pass

class FollowRouteScenario(Scenario):
    """Simple scenario where vehicle must follow a route with waypoints"""
    def __init__(self, world_manager, vehicle_manager, num_waypoints=5):
        super().__init__(world_manager, vehicle_manager)
        self.num_waypoints = num_waypoints
        self.waypoints: List[carla.Location] = []
        self.current_waypoint = 0
        self.waypoint_tolerance = 5.0  # meters

    def setup(self):
        # Generate a series of waypoints
        current_point = self.vehicle_manager.vehicle.get_location()
        for _ in range(self.num_waypoints):
            # Get random point 50-100 meters away
            distance = random.uniform(50, 100)
            angle = random.uniform(0, 2 * math.pi)
            
            # Calculate next point
            next_x = current_point.x + distance * math.cos(angle)
            next_y = current_point.y + distance * math.sin(angle)
            
            # Get valid waypoint on road
            waypoint = self.world_manager.world.get_map().get_waypoint(
                carla.Location(x=next_x, y=next_y, z=current_point.z),
                project_to_road=True
            )
            
            self.waypoints.append(waypoint.transform.location)
            current_point = waypoint.transform.location

        # Set first waypoint as target
        self.vehicle_manager.set_target(self.waypoints[0])
        self.start_time = time.time()
        
        # Log scenario start
        if hasattr(self.vehicle_manager, 'logger') and self.vehicle_manager.logger:
            self.vehicle_manager.logger.log_info(f"Follow route scenario started with {self.num_waypoints} waypoints.")

    def update(self):
        if self.is_completed:
            return

        # Check distance to current waypoint
        current_loc = self.vehicle_manager.vehicle.get_location()
        distance = current_loc.distance(self.waypoints[self.current_waypoint])

        if distance < self.waypoint_tolerance:
            self.current_waypoint += 1
            if self.current_waypoint >= len(self.waypoints):
                self.is_completed = True
                self.success = True
                self.completion_time = time.time() - self.start_time
                # Log scenario completion
                if hasattr(self.vehicle_manager, 'logger') and self.vehicle_manager.logger:
                    self.vehicle_manager.logger.log_info(f"Scenario completed successfully in {self.completion_time:.1f} seconds!")
            else:
                # Set next waypoint as target
                self.vehicle_manager.set_target(self.waypoints[self.current_waypoint])
                # Log waypoint reached
                if hasattr(self.vehicle_manager, 'logger') and self.vehicle_manager.logger:
                    self.vehicle_manager.logger.log_info(f"Reached waypoint {self.current_waypoint}/{len(self.waypoints)}")

class AvoidObstacleScenario(Scenario):
    """Scenario where vehicle must avoid static obstacles on the road"""
    def __init__(self, world_manager, vehicle_manager, num_obstacles=3):
        super().__init__(world_manager, vehicle_manager)
        self.num_obstacles = num_obstacles
        self.obstacles = []
        self.target_distance = 100.0  # meters
        self.obstacle_spacing = self.target_distance / (self.num_obstacles + 1)
        self.completion_distance = self.target_distance + 10.0
        self.initial_speed = 20.0  # km/h - reduced speed for better control
        self.obstacle_blueprints = [
            'static.prop.streetbarrier',
            'static.prop.trafficcone01',
            'static.prop.trafficcone02'
        ]
        self.max_attempts = 3  # Maximum attempts to spawn obstacles
        self.current_attempt = 0

    def setup(self):
        try:
            # Get vehicle's current position and forward vector
            vehicle_transform = self.vehicle_manager.vehicle.get_transform()
            forward_vector = vehicle_transform.get_forward_vector()
            
            # Set initial speed for better control
            self.vehicle_manager.vehicle.set_target_velocity(
                carla.Vector3D(x=self.initial_speed/3.6, y=0.0, z=0.0)
            )
            
            # Calculate target point straight ahead
            target_location = carla.Location(
                x=vehicle_transform.location.x + forward_vector.x * self.target_distance,
                y=vehicle_transform.location.y + forward_vector.y * self.target_distance,
                z=vehicle_transform.location.z
            )
            
            # Get the waypoint for the target
            target_waypoint = self.world_manager.world.get_map().get_waypoint(target_location)
            if target_waypoint:
                target_location = target_waypoint.transform.location
            
            # Set the final target
            self.vehicle_manager.set_target(target_location)
            
            # Spawn obstacles along the path with better spacing and placement
            for i in range(self.num_obstacles):
                # Calculate base distance for this obstacle
                distance = self.obstacle_spacing * (i + 1)
                
                # Get the waypoint at this distance
                obstacle_waypoint = self.world_manager.world.get_map().get_waypoint(
                    carla.Location(
                        x=vehicle_transform.location.x + forward_vector.x * distance,
                        y=vehicle_transform.location.y + forward_vector.y * distance,
                        z=vehicle_transform.location.z
                    )
                )
                
                if obstacle_waypoint:
                    # Get the next waypoint to determine road direction
                    next_waypoint = obstacle_waypoint.next(1.0)[0]
                    road_direction = next_waypoint.transform.location - obstacle_waypoint.transform.location
                    road_direction = road_direction.make_unit_vector()
                    
                    # Calculate perpendicular offset (alternating sides)
                    perpendicular_offset = 4.0 if i % 2 == 0 else -4.0
                    
                    # Calculate obstacle position with offset perpendicular to road direction
                    obstacle_location = carla.Location(
                        x=obstacle_waypoint.transform.location.x + perpendicular_offset * road_direction.y,
                        y=obstacle_waypoint.transform.location.y - perpendicular_offset * road_direction.x,
                        z=obstacle_waypoint.transform.location.z
                    )
                    
                    # Choose a random obstacle blueprint
                    blueprint_name = random.choice(self.obstacle_blueprints)
                    blueprint = self.world_manager.world.get_blueprint_library().find(blueprint_name)
                    
                    # Spawn the obstacle
                    obstacle_transform = carla.Transform(obstacle_location)
                    obstacle = self.world_manager.world.spawn_actor(blueprint, obstacle_transform)
                    if obstacle:
                        self.obstacles.append(obstacle)
                        if hasattr(self.vehicle_manager, 'logger') and self.vehicle_manager.logger:
                            self.vehicle_manager.logger.log_info(f"Spawned obstacle {i+1} at distance {distance:.1f}m with offset {perpendicular_offset:.1f}m")
            
            self.start_time = time.time()
            if hasattr(self.vehicle_manager, 'logger') and self.vehicle_manager.logger:
                self.vehicle_manager.logger.log_info(f"Avoid obstacle scenario started with {len(self.obstacles)} obstacles")
                self.vehicle_manager.logger.log_info(f"Initial speed set to {self.initial_speed} km/h for better control")
        
        except Exception as e:
            if hasattr(self.vehicle_manager, 'logger') and self.vehicle_manager.logger:
                self.vehicle_manager.logger.log_error(f"Error in AvoidObstacleScenario setup: {str(e)}")
            # Mark scenario as completed but failed
            self.is_completed = True
            self.success = False
            self.cleanup()  # Clean up any spawned obstacles

    def update(self):
        if self.is_completed:
            return

        try:
            # Get current vehicle state
            vehicle_location = self.vehicle_manager.vehicle.get_location()
            target_location = self.vehicle_manager._target_point
            vehicle_velocity = self.vehicle_manager.vehicle.get_velocity()
            speed = 3.6 * math.sqrt(vehicle_velocity.x**2 + vehicle_velocity.y**2)  # km/h
            
            # Check if vehicle has reached the target
            distance_to_target = vehicle_location.distance(target_location)
            
            # Check for collisions with obstacles
            for obstacle in self.obstacles:
                if obstacle and obstacle.is_active:
                    obstacle_location = obstacle.get_location()
                    distance = vehicle_location.distance(obstacle_location)
                    if distance < 2.5:  # Increased collision threshold
                        self.is_completed = True
                        self.success = False
                        if hasattr(self.vehicle_manager, 'logger') and self.vehicle_manager.logger:
                            self.vehicle_manager.logger.log_info(f"Failed: Collision with obstacle at distance {distance:.1f}m!")
                        return
            
            # Check if passed all obstacles successfully
            if distance_to_target < 5.0:
                self.is_completed = True
                self.success = True
                self.completion_time = time.time() - self.start_time
                if hasattr(self.vehicle_manager, 'logger') and self.vehicle_manager.logger:
                    self.vehicle_manager.logger.log_info(f"Successfully avoided all obstacles! Time: {self.completion_time:.1f} seconds")
        
        except Exception as e:
            if hasattr(self.vehicle_manager, 'logger') and self.vehicle_manager.logger:
                self.vehicle_manager.logger.log_error(f"Error in AvoidObstacleScenario update: {str(e)}")
            # Mark scenario as completed but failed
            self.is_completed = True
            self.success = False
            self.cleanup()  # Clean up any spawned obstacles

    def cleanup(self):
        try:
            for obstacle in self.obstacles:
                if obstacle and obstacle.is_active:
                    obstacle.destroy()
            self.obstacles = []
        except Exception as e:
            if hasattr(self.vehicle_manager, 'logger') and self.vehicle_manager.logger:
                self.vehicle_manager.logger.log_error(f"Error in AvoidObstacleScenario cleanup: {str(e)}")

class EmergencyBrakeScenario(Scenario):
    """Scenario where vehicle must perform emergency braking when an obstacle suddenly appears"""
    def __init__(self, world_manager, vehicle_manager):
        super().__init__(world_manager, vehicle_manager)
        self.obstacle = None
        self.trigger_distance = 50.0  # meters
        self.obstacle_spawned = False
        self.safe_stop_distance = 3.0  # meters
        self.initial_speed = 50.0  # km/h

    def setup(self):
        # Set initial speed
        self.vehicle_manager.vehicle.set_target_velocity(
            carla.Vector3D(x=self.initial_speed/3.6, y=0.0, z=0.0)
        )
        
        # Get vehicle's transform
        vehicle_transform = self.vehicle_manager.vehicle.get_transform()
        forward_vector = vehicle_transform.get_forward_vector()
        
        # Calculate target point
        self.target_location = carla.Location(
            x=vehicle_transform.location.x + forward_vector.x * (self.trigger_distance + 20.0),
            y=vehicle_transform.location.y + forward_vector.y * (self.trigger_distance + 20.0),
            z=vehicle_transform.location.z
        )
        
        self.vehicle_manager.set_target(self.target_location)
        self.start_time = time.time()
        if hasattr(self.vehicle_manager, 'logger') and self.vehicle_manager.logger:
            self.vehicle_manager.logger.log_info(f"Emergency brake scenario started. Target speed: {self.initial_speed} km/h")

    def update(self):
        if self.is_completed:
            return

        # Get current vehicle state
        vehicle_transform = self.vehicle_manager.vehicle.get_transform()
        vehicle_velocity = self.vehicle_manager.vehicle.get_velocity()
        speed = 3.6 * math.sqrt(vehicle_velocity.x**2 + vehicle_velocity.y**2)  # km/h

        # Wait until vehicle reaches target speed
        if not self.obstacle_spawned and speed >= self.initial_speed * 0.9:
            # Spawn obstacle suddenly in front of vehicle
            forward_vector = vehicle_transform.get_forward_vector()
            obstacle_location = carla.Location(
                x=vehicle_transform.location.x + forward_vector.x * self.trigger_distance,
                y=vehicle_transform.location.y + forward_vector.y * self.trigger_distance,
                z=vehicle_transform.location.z
            )
            
            blueprint = self.world_manager.world.get_blueprint_library().find('static.prop.streetbarrier')
            obstacle_transform = carla.Transform(obstacle_location)
            self.obstacle = self.world_manager.world.spawn_actor(blueprint, obstacle_transform)
            self.obstacle_spawned = True
            if hasattr(self.vehicle_manager, 'logger') and self.vehicle_manager.logger:
                self.vehicle_manager.logger.log_info("Obstacle spawned! Emergency brake required!")

        if self.obstacle_spawned:
            # Check distance to obstacle
            distance_to_obstacle = vehicle_transform.location.distance(self.obstacle.get_location())
            
            # Check if stopped safely
            if speed < 1.0 and distance_to_obstacle > self.safe_stop_distance:
                self.is_completed = True
                self.success = True
                self.completion_time = time.time() - self.start_time
                if hasattr(self.vehicle_manager, 'logger') and self.vehicle_manager.logger:
                    self.vehicle_manager.logger.log_info(f"Successfully performed emergency brake! Time: {self.completion_time:.1f} seconds")
            elif distance_to_obstacle < self.safe_stop_distance:
                self.is_completed = True
                self.success = False
                if hasattr(self.vehicle_manager, 'logger') and self.vehicle_manager.logger:
                    self.vehicle_manager.logger.log_info("Failed: Collision with obstacle!")

    def cleanup(self):
        if self.obstacle is not None:
            self.obstacle.destroy()

class VehicleCuttingScenario(Scenario):
    """Scenario where another vehicle cuts in front of the ego vehicle"""
    def __init__(self, world_manager, vehicle_manager):
        super().__init__(world_manager, vehicle_manager)
        self.cutting_vehicle = None
        self.initial_distance = 40.0  # meters
        self.cutting_distance = 20.0  # meters
        self.safe_distance = 5.0  # meters
        self.target_speed = 40.0  # km/h
        self.is_cutting = False
        self.cut_complete = False
        self.max_spawn_attempts = 5  # Maximum attempts to spawn the cutting vehicle

    def setup(self):
        try:
            # Get ego vehicle's transform
            ego_transform = self.vehicle_manager.vehicle.get_transform()
            forward_vector = ego_transform.get_forward_vector()
            right_vector = ego_transform.get_right_vector()
            
            # Try different spawn positions
            for attempt in range(self.max_spawn_attempts):
                try:
                    # Calculate spawn point for cutting vehicle (to the right of ego vehicle)
                    # Adjust distance and offset based on attempt
                    distance = self.initial_distance + (attempt * 5.0)  # Increase distance with each attempt
                    offset = 3.5 + (attempt * 0.5)  # Increase offset with each attempt
                    
                    spawn_location = carla.Location(
                        x=ego_transform.location.x + forward_vector.x * distance + right_vector.x * offset,
                        y=ego_transform.location.y + forward_vector.y * distance + right_vector.y * offset,
                        z=ego_transform.location.z
                    )
                    
                    # Get the waypoint for spawn location
                    spawn_waypoint = self.world_manager.world.get_map().get_waypoint(spawn_location)
                    if spawn_waypoint:
                        spawn_location = spawn_waypoint.transform.location
                    
                    spawn_rotation = ego_transform.rotation
                    spawn_transform = carla.Transform(spawn_location, spawn_rotation)
                    
                    # Spawn the cutting vehicle
                    blueprint = self.world_manager.world.get_blueprint_library().find('vehicle.fuso.mitsubishi')
                    blueprint.set_attribute('role_name', 'cutting_vehicle')
                    self.cutting_vehicle = self.world_manager.world.spawn_actor(blueprint, spawn_transform)
                    
                    if self.cutting_vehicle:
                        if hasattr(self.vehicle_manager, 'logger') and self.vehicle_manager.logger:
                            self.vehicle_manager.logger.log_info(f"Successfully spawned cutting vehicle on attempt {attempt + 1}")
                        break
                        
                except Exception as e:
                    if hasattr(self.vehicle_manager, 'logger') and self.vehicle_manager.logger:
                        self.vehicle_manager.logger.log_info(f"Spawn attempt {attempt + 1} failed: {str(e)}")
                    if attempt == self.max_spawn_attempts - 1:
                        raise RuntimeError(f"Failed to spawn cutting vehicle after {self.max_spawn_attempts} attempts")
                    continue
            
            # Set target point far ahead
            target_location = carla.Location(
                x=ego_transform.location.x + forward_vector.x * (self.initial_distance + 100.0),
                y=ego_transform.location.y + forward_vector.y * (self.initial_distance + 100.0),
                z=ego_transform.location.z
            )
            self.vehicle_manager.set_target(target_location)
            
            # Set initial velocity for cutting vehicle
            self.cutting_vehicle.set_target_velocity(carla.Vector3D(x=self.target_speed/3.6, y=0, z=0))
            
            self.start_time = time.time()
            if hasattr(self.vehicle_manager, 'logger') and self.vehicle_manager.logger:
                self.vehicle_manager.logger.log_info("Vehicle cutting scenario started")
        
        except Exception as e:
            if hasattr(self.vehicle_manager, 'logger') and self.vehicle_manager.logger:
                self.vehicle_manager.logger.log_error(f"Error in VehicleCuttingScenario setup: {str(e)}")
            # Mark scenario as completed but failed
            self.is_completed = True
            self.success = False
            self.cleanup()  # Clean up any spawned vehicles
            raise  # Re-raise the exception to be handled by the main loop

    def update(self):
        if self.is_completed:
            return

        # Get vehicle states
        ego_location = self.vehicle_manager.vehicle.get_location()
        cutting_location = self.cutting_vehicle.get_location()
        ego_velocity = self.vehicle_manager.vehicle.get_velocity()
        ego_speed = 3.6 * math.sqrt(ego_velocity.x**2 + ego_velocity.y**2)  # km/h
        
        # Calculate distance between vehicles
        distance = ego_location.distance(cutting_location)
        
        # Start cutting maneuver when ego vehicle is close enough
        if not self.is_cutting and distance < self.cutting_distance:
            self.is_cutting = True
            # Calculate cutting trajectory
            ego_transform = self.vehicle_manager.vehicle.get_transform()
            forward_vector = ego_transform.get_forward_vector()
            target_location = carla.Location(
                x=ego_location.x + forward_vector.x * 10.0,
                y=ego_location.y + forward_vector.y * 10.0,
                z=ego_location.z
            )
            # Make the cutting vehicle move in front
            self.cutting_vehicle.set_transform(carla.Transform(
                target_location,
                ego_transform.rotation
            ))
            if hasattr(self.vehicle_manager, 'logger') and self.vehicle_manager.logger:
                self.vehicle_manager.logger.log_info("Vehicle cutting in!")

        # Check for collision
        if distance < self.safe_distance:
            self.is_completed = True
            self.success = False
            if hasattr(self.vehicle_manager, 'logger') and self.vehicle_manager.logger:
                self.vehicle_manager.logger.log_info("Failed: Too close to cutting vehicle!")
            return
        
        # Check if cut is complete
        if self.is_cutting and not self.cut_complete and distance > self.cutting_distance:
            self.cut_complete = True
            if hasattr(self.vehicle_manager, 'logger') and self.vehicle_manager.logger:
                self.vehicle_manager.logger.log_info("Cut completed successfully!")
        
        # Check if scenario is complete (cut performed and safe distance maintained)
        if self.cut_complete and ego_speed > 0 and distance > self.safe_distance:
            self.is_completed = True
            self.success = True
            self.completion_time = time.time() - self.start_time
            if hasattr(self.vehicle_manager, 'logger') and self.vehicle_manager.logger:
                self.vehicle_manager.logger.log_info(f"Successfully handled vehicle cutting! Time: {self.completion_time:.1f} seconds")

    def cleanup(self):
        if self.cutting_vehicle is not None:
            self.cutting_vehicle.destroy()

class PedestrianCrossingScenario(Scenario):
    """Scenario where a pedestrian crosses the road in front of the vehicle"""
    def __init__(self, world_manager, vehicle_manager):
        super().__init__(world_manager, vehicle_manager)
        self.pedestrian = None
        self.controller = None
        self.crossing_distance = 30.0  # meters
        self.safe_distance = 3.0  # meters
        self.is_crossing = False
        self.cross_complete = False
        self.initial_speed = 40.0  # km/h
        self.max_spawn_attempts = 5  # Maximum attempts to spawn the pedestrian
        # CARLA 0.10.0 official pedestrian blueprints
        self.pedestrian_blueprints = [
            'walker.pedestrian.0001',
            'walker.pedestrian.0002',
            'walker.pedestrian.0003',
            'walker.pedestrian.0004',
            'walker.pedestrian.0005',
            'walker.pedestrian.0006',
            'walker.pedestrian.0007',
            'walker.pedestrian.0008',
            'walker.pedestrian.0009',
            'walker.pedestrian.0010',
            'walker.pedestrian.0011',
            'walker.pedestrian.0012',
            'walker.pedestrian.0013',
            'walker.pedestrian.0014',
            'walker.pedestrian.0015',
            'walker.pedestrian.0016'
        ]

    def find_valid_spawn_point(self, ego_transform, attempt):
        """Find a valid spawn point for the pedestrian using the navigation mesh"""
        try:
            # Get the map and navigation mesh
            carla_map = self.world_manager.world.get_map()
            
            # Calculate base spawn location
            forward_vector = ego_transform.get_forward_vector()
            right_vector = ego_transform.get_right_vector()
            
            # Adjust distance and offset based on attempt
            distance = self.crossing_distance + (attempt * 5.0)
            offset = 4.0 + (attempt * 0.5)
            
            # Calculate initial spawn location
            spawn_location = carla.Location(
                x=ego_transform.location.x + forward_vector.x * distance + right_vector.x * offset,
                y=ego_transform.location.y + forward_vector.y * distance + right_vector.y * offset,
                z=ego_transform.location.z
            )
            
            # Get the waypoint for spawn location
            spawn_waypoint = carla_map.get_waypoint(spawn_location)
            if not spawn_waypoint:
                return None
            
            # Get the sidewalk waypoint
            sidewalk_waypoint = spawn_waypoint.get_right_lane()
            if not sidewalk_waypoint:
                return None
            
            # Get the spawn location from the sidewalk waypoint
            spawn_location = sidewalk_waypoint.transform.location
            
            # Ensure the spawn location is on the ground
            spawn_location.z += 1.0  # Add a small offset to ensure it's above ground
            
            return spawn_location
            
        except Exception as e:
            if hasattr(self.vehicle_manager, 'logger') and self.vehicle_manager.logger:
                self.vehicle_manager.logger.log_error(f"Error finding valid spawn point: {str(e)}")
            return None

    def setup(self):
        try:
            # Set initial speed for ego vehicle
            self.vehicle_manager.vehicle.set_target_velocity(
                carla.Vector3D(x=self.initial_speed/3.6, y=0.0, z=0.0)
            )
            
            # Get ego vehicle's transform
            ego_transform = self.vehicle_manager.vehicle.get_transform()
            
            # Try different spawn positions
            for attempt in range(self.max_spawn_attempts):
                try:
                    # Find valid spawn point
                    spawn_location = self.find_valid_spawn_point(ego_transform, attempt)
                    if not spawn_location:
                        if hasattr(self.vehicle_manager, 'logger') and self.vehicle_manager.logger:
                            self.vehicle_manager.logger.log_info(f"Could not find valid spawn point on attempt {attempt + 1}")
                        continue
                    
                    # Try different pedestrian blueprints
                    for blueprint_name in self.pedestrian_blueprints:
                        try:
                            blueprint = self.world_manager.world.get_blueprint_library().find(blueprint_name)
                            if not blueprint:
                                if hasattr(self.vehicle_manager, 'logger') and self.vehicle_manager.logger:
                                    self.vehicle_manager.logger.log_info(f"Blueprint {blueprint_name} not found, trying next")
                                continue
                                
                            # Set pedestrian attributes
                            blueprint.set_attribute('is_invincible', 'true')
                            blueprint.set_attribute('speed', '1.4')
                            
                            # Create spawn transform
                            spawn_transform = carla.Transform(
                                spawn_location,
                                carla.Rotation(pitch=0.0, yaw=ego_transform.rotation.yaw, roll=0.0)
                            )
                            
                            # Try to spawn the pedestrian
                            self.pedestrian = self.world_manager.world.spawn_actor(blueprint, spawn_transform)
                            
                            if self.pedestrian:
                                if hasattr(self.vehicle_manager, 'logger') and self.vehicle_manager.logger:
                                    self.vehicle_manager.logger.log_info(f"Successfully spawned pedestrian {blueprint_name} on attempt {attempt + 1}")
                                break
                                
                        except Exception as e:
                            if hasattr(self.vehicle_manager, 'logger') and self.vehicle_manager.logger:
                                self.vehicle_manager.logger.log_info(f"Failed to spawn {blueprint_name} on attempt {attempt + 1}: {str(e)}")
                            continue
                    
                    if self.pedestrian:
                        break
                        
                except Exception as e:
                    if hasattr(self.vehicle_manager, 'logger') and self.vehicle_manager.logger:
                        self.vehicle_manager.logger.log_info(f"Spawn attempt {attempt + 1} failed: {str(e)}")
                    if attempt == self.max_spawn_attempts - 1:
                        raise RuntimeError(f"Failed to spawn pedestrian after {self.max_spawn_attempts} attempts")
                    continue
            
            if not self.pedestrian:
                raise RuntimeError("Failed to spawn pedestrian with any blueprint")
            
            # Set target point far ahead for ego vehicle
            forward_vector = ego_transform.get_forward_vector()
            target_location = carla.Location(
                x=ego_transform.location.x + forward_vector.x * (self.crossing_distance + 100.0),
                y=ego_transform.location.y + forward_vector.y * (self.crossing_distance + 100.0),
                z=ego_transform.location.z
            )
            self.vehicle_manager.set_target(target_location)
            
            # Create and start walker AI controller
            walker_controller_bp = self.world_manager.world.get_blueprint_library().find('controller.ai.walker')
            if not walker_controller_bp:
                raise RuntimeError("Failed to find walker controller blueprint")
                
            self.controller = self.world_manager.world.spawn_actor(walker_controller_bp, carla.Transform(), self.pedestrian)
            if not self.controller:
                raise RuntimeError("Failed to spawn walker controller")
            
            self.start_time = time.time()
            if hasattr(self.vehicle_manager, 'logger') and self.vehicle_manager.logger:
                self.vehicle_manager.logger.log_info("Pedestrian crossing scenario started")
        
        except Exception as e:
            if hasattr(self.vehicle_manager, 'logger') and self.vehicle_manager.logger:
                self.vehicle_manager.logger.log_error(f"Error in PedestrianCrossingScenario setup: {str(e)}")
            # Mark scenario as completed but failed
            self.is_completed = True
            self.success = False
            self.cleanup()  # Clean up any spawned actors
            raise  # Re-raise the exception to be handled by the main loop

    def update(self):
        if self.is_completed:
            return

        try:
            # Get current states
            ego_location = self.vehicle_manager.vehicle.get_location()
            pedestrian_location = self.pedestrian.get_location()
            ego_velocity = self.vehicle_manager.vehicle.get_velocity()
            ego_speed = 3.6 * math.sqrt(ego_velocity.x**2 + ego_velocity.y**2)  # km/h
            
            # Calculate distance between vehicle and pedestrian
            distance = ego_location.distance(pedestrian_location)
            
            # Start crossing when vehicle is close enough
            if not self.is_crossing and distance < self.crossing_distance:
                self.is_crossing = True
                # Calculate crossing target (other side of the road)
                ego_transform = self.vehicle_manager.vehicle.get_transform()
                right_vector = ego_transform.get_right_vector()
                target_location = carla.Location(
                    x=pedestrian_location.x - right_vector.x * 8.0,
                    y=pedestrian_location.y - right_vector.y * 8.0,
                    z=pedestrian_location.z
                )
                # Command pedestrian to cross
                self.controller.start()
                self.controller.go_to_location(target_location)
                self.controller.set_max_speed(1.4)  # normal walking speed
                if hasattr(self.vehicle_manager, 'logger') and self.vehicle_manager.logger:
                    self.vehicle_manager.logger.log_info("Pedestrian starting to cross!")

            # Check for collision
            if distance < self.safe_distance:
                self.is_completed = True
                self.success = False
                if hasattr(self.vehicle_manager, 'logger') and self.vehicle_manager.logger:
                    self.vehicle_manager.logger.log_info("Failed: Too close to pedestrian!")
                return
            
            # Check if crossing is complete
            if self.is_crossing and not self.cross_complete:
                # Check if pedestrian has reached the other side
                ego_transform = self.vehicle_manager.vehicle.get_transform()
                right_vector = ego_transform.get_right_vector()
                cross_vector = carla.Vector3D(
                    x=-right_vector.x * 8.0,
                    y=-right_vector.y * 8.0,
                    z=0
                )
                if pedestrian_location.distance(ego_location + cross_vector) < 1.0:
                    self.cross_complete = True
                    if hasattr(self.vehicle_manager, 'logger') and self.vehicle_manager.logger:
                        self.vehicle_manager.logger.log_info("Pedestrian crossed successfully!")
            
            # Check if scenario is complete (crossing performed and safe distance maintained)
            if self.cross_complete and ego_speed > 0 and distance > self.safe_distance:
                self.is_completed = True
                self.success = True
                self.completion_time = time.time() - self.start_time
                if hasattr(self.vehicle_manager, 'logger') and self.vehicle_manager.logger:
                    self.vehicle_manager.logger.log_info(f"Successfully handled pedestrian crossing! Time: {self.completion_time:.1f} seconds")
        
        except Exception as e:
            if hasattr(self.vehicle_manager, 'logger') and self.vehicle_manager.logger:
                self.vehicle_manager.logger.log_error(f"Error in PedestrianCrossingScenario update: {str(e)}")
            # Mark scenario as completed but failed
            self.is_completed = True
            self.success = False
            self.cleanup()  # Clean up any spawned actors

    def cleanup(self):
        try:
            if self.controller is not None:
                try:
                    self.controller.stop()
                    self.controller.destroy()
                except Exception as e:
                    if hasattr(self.vehicle_manager, 'logger') and self.vehicle_manager.logger:
                        self.vehicle_manager.logger.log_error(f"Error stopping controller: {str(e)}")
                self.controller = None
            
            if self.pedestrian is not None:
                try:
                    self.pedestrian.destroy()
                except Exception as e:
                    if hasattr(self.vehicle_manager, 'logger') and self.vehicle_manager.logger:
                        self.vehicle_manager.logger.log_error(f"Error destroying pedestrian: {str(e)}")
                self.pedestrian = None
        except Exception as e:
            if hasattr(self.vehicle_manager, 'logger') and self.vehicle_manager.logger:
                self.vehicle_manager.logger.log_error(f"Error in PedestrianCrossingScenario cleanup: {str(e)}")

def find_available_tm_port(client):
    """Find an available Traffic Manager port using random ports"""
    base_port = 8000
    max_attempts = 20
    
    # Try ports in sequence first
    for port in range(base_port, base_port + 10):
        try:
            tm = client.get_trafficmanager(port)
            tm.set_synchronous_mode(True)
            print(f"Found available Traffic Manager port: {port}")
            return port
        except Exception:
            continue
    
    # If sequential ports fail, try random ports
    ports_to_try = random.sample(range(base_port, base_port + 1000), max_attempts)
    for port in ports_to_try:
        try:
            tm = client.get_trafficmanager(port)
            tm.set_synchronous_mode(True)
            print(f"Found available Traffic Manager port: {port}")
            return port
        except Exception:
            continue
    
    raise RuntimeError("Could not find available Traffic Manager port")

class CarlaSimulator:
    """Main simulator class coordinating all components"""
    
    def __init__(self, config_path: str, scenario_type: ScenarioType = ScenarioType.FOLLOW_ROUTE):
        """Initialize simulator with configuration"""
        # Load configuration
        self.config = load_config(config_path)
        self.scenario_type = scenario_type
        
        # Initialize logging
        self.logger = SimulationLogger(self.config.logging)
        
        # Initialize components
        self.world_manager = None
        self.vehicle_manager = None
        self.sensor_manager = None
        self.display_manager = None
        self.controller = None
        self.client = None
        
        # Initialize state
        self.is_running = False
        self.start_time = None
        self.current_scenario = None
        self.tm_port = None  # Store traffic manager port

    def connect_to_server(self) -> bool:
        """Attempt to connect to CARLA server with proper error handling"""
        max_retries = 3
        retry_delay = 5  # seconds
        
        for attempt in range(max_retries):
            try:
                self.logger.log_info(f"Attempting to connect to CARLA server (attempt {attempt + 1}/{max_retries})")
                # Create client with timeout
                self.client = carla.Client(self.config.server.host, self.config.server.port)
                self.client.set_timeout(self.config.server.timeout)
                
                # Test connection
                world = self.client.get_world()
                self.logger.log_info(f"Successfully connected to CARLA server. Map: {world.get_map().name}")
                return True
                
            except Exception as e:
                self.logger.log_error(f"Connection attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    self.logger.log_info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    self.logger.log_error("Failed to connect to CARLA server after all attempts")
                    return False
        
        return False

    def setup(self) -> None:
        """Set up simulation components"""
        try:
            self.logger.log_info("Starting simulation setup...")
            
            # First connect to server
            if not self.connect_to_server():
                raise RuntimeError("Unable to connect to CARLA server")
            
            # Get world and apply settings
            self.world = self.client.get_world()
            self.logger.log_info("World settings applied")
            
            # Set up synchronous mode first
            settings = self.world.get_settings()
            settings.synchronous_mode = True
            settings.fixed_delta_seconds = 1.0 / self.config.simulation.update_rate
            self.world.apply_settings(settings)
            self.logger.log_info("Synchronous mode enabled")
            
            # Initialize managers
            self.logger.log_info("Initializing world manager...")
            self.world_manager = WorldManager(self.client, self.config.world)
            
            self.logger.log_info("Initializing vehicle manager...")
            self.vehicle_manager = VehicleManager(self.world, self.config.vehicle_model)
            
            # Spawn vehicle
            self.logger.log_info("Getting spawn point...")
            spawn_point = self.world_manager.get_random_spawn_point()
            if not spawn_point:
                raise RuntimeError("Failed to get valid spawn point")
            
            self.logger.log_info("Spawning vehicle...")
            self.vehicle_manager.spawn_vehicle(spawn_point)
            
            # Wait for vehicle to be properly spawned
            self.world.tick()
            self.logger.log_info("Vehicle spawned successfully")
            
            # Get vehicle transform and ensure it's valid
            vehicle_transform = self.vehicle_manager.vehicle.get_transform()
            if not vehicle_transform or not vehicle_transform.location:
                raise RuntimeError("Failed to get valid vehicle transform")
            
            # Generate target point using WorldManager
            self.logger.log_info("Generating target point...")
            target_point = self.world_manager.generate_target_point(vehicle_transform)
            if not target_point or not target_point.location:
                raise RuntimeError("Failed to generate valid target point")
            
            # Set target and verify it was set
            self.vehicle_manager.set_target(target_point.location)
            self.logger.log_info("Target point set successfully")
            
            # Wait for target to be properly set
            self.world.tick()
            
            # Verify target was set correctly
            if not self.vehicle_manager._target_point:
                raise RuntimeError("Failed to set target point in vehicle manager")
            
            # Set up autopilot if enabled
            if self.config.controller.type == 'autopilot':
                try:
                    self.logger.log_info("Setting up autopilot...")
                    # Find available Traffic Manager port
                    self.tm_port = find_available_tm_port(self.client)
                    
                    # Get traffic manager with specific port
                    traffic_manager = self.client.get_trafficmanager(self.tm_port)
                    traffic_manager.set_synchronous_mode(True)
                    
                    # Enable autopilot with traffic manager port
                    self.vehicle_manager.vehicle.set_autopilot(True, self.tm_port)
                    
                    # Configure vehicle behavior
                    traffic_manager.set_global_distance_to_leading_vehicle(3.5)
                    traffic_manager.vehicle_percentage_speed_difference(self.vehicle_manager.vehicle, 0)
                    traffic_manager.ignore_lights_percentage(self.vehicle_manager.vehicle, 0)
                    traffic_manager.ignore_signs_percentage(self.vehicle_manager.vehicle, 0)
                    traffic_manager.auto_lane_change(self.vehicle_manager.vehicle, True)
                    traffic_manager.random_left_lanechange_percentage(self.vehicle_manager.vehicle, 0)
                    traffic_manager.random_right_lanechange_percentage(self.vehicle_manager.vehicle, 0)
                    
                    # Set initial speed and remove speed limits
                    initial_speed = 120.0  # km/h
                    traffic_manager.set_desired_speed(self.vehicle_manager.vehicle, initial_speed)
                    traffic_manager.vehicle_percentage_speed_difference(self.vehicle_manager.vehicle, 0)  # No speed reduction
                    traffic_manager.set_global_distance_to_leading_vehicle(3.5)  # Minimum safe distance
                    
                    self.logger.log_info("Autopilot configured successfully")
                except Exception as e:
                    self.logger.log_error(f"Failed to setup autopilot: {str(e)}")
                    # Silently fall back to manual control
                    self.config.controller.type = 'keyboard'
            
            # Initialize sensors
            self.logger.log_info("Initializing sensor manager...")
            self.sensor_manager = SensorManager(self.vehicle_manager.vehicle, self.config.sensors)
            
            # Initialize display
            self.logger.log_info("Initializing display manager...")
            self.display_manager = DisplayManager(self.config.display)
            
            # Add camera view as sensor observer
            self.sensor_manager.add_observer('camera', self.display_manager.camera_view)
            
            # Initialize controller
            self.logger.log_info("Initializing controller...")
            self.controller = VehicleController(self.config.controller)
            
            # Set control strategy based on configuration
            if self.config.controller.type == 'keyboard':
                self.controller.set_strategy(KeyboardController(self.config.controller, self.logger))
            elif self.config.controller.type == 'gamepad':
                self.controller.set_strategy(GamepadController(self.config.controller))
            elif self.config.controller.type == 'autopilot':
                self.controller.set_strategy(AutopilotController(self.vehicle_manager.vehicle, self.config.controller, self.client))
            else:
                raise ValueError(f"Unknown controller type: {self.config.controller.type}")
            
            # Setup scenario using the specified type
            self.logger.log_info(f"Setting up scenario: {self.scenario_type.name}")
            self.setup_scenario(self.scenario_type)
            
            self.logger.log_info("Simulation setup completed successfully")
            
        except Exception as e:
            self.logger.log_error(f"Error during setup: {str(e)}")
            import traceback
            self.logger.log_error(f"Setup traceback: {traceback.format_exc()}")
            self.cleanup()
            raise
    
    def setup_scenario(self, scenario_type: ScenarioType) -> None:
        """Set up a specific scenario"""
        if scenario_type == ScenarioType.FOLLOW_ROUTE:
            self.current_scenario = FollowRouteScenario(self.world_manager, self.vehicle_manager)
        elif scenario_type == ScenarioType.AVOID_OBSTACLE:
            self.current_scenario = AvoidObstacleScenario(self.world_manager, self.vehicle_manager)
        elif scenario_type == ScenarioType.EMERGENCY_BRAKE:
            self.current_scenario = EmergencyBrakeScenario(self.world_manager, self.vehicle_manager)
        elif scenario_type == ScenarioType.VEHICLE_CUTTING:
            self.current_scenario = VehicleCuttingScenario(self.world_manager, self.vehicle_manager)
        elif scenario_type == ScenarioType.PEDESTRIAN_CROSSING:
            self.current_scenario = PedestrianCrossingScenario(self.world_manager, self.vehicle_manager)
        
        if self.current_scenario:
            self.current_scenario.setup()
    
    def run(self) -> None:
        """Run the main simulation loop"""
        try:
            self.is_running = True
            self.start_time = time.time()
            self.scenario_quit = False  # Flag to indicate scenario quit vs full quit
            
            while self.is_running:
                try:
                    # Handle pygame events
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            self.logger.log_info("Pygame window closed by user")
                            self.is_running = False
                            self.full_exit = True
                            break
                        elif event.type == pygame.KEYDOWN:
                            if event.key == pygame.K_ESCAPE:
                                self.logger.log_info("Escape key pressed, exiting entire simulation")
                                self.is_running = False
                                self.full_exit = True
                                break
                            elif event.key == pygame.K_q:
                                self.logger.log_info("Q key pressed, moving to next scenario")
                                self.is_running = False
                                self.scenario_quit = True  # Set scenario quit flag
                                # Mark current scenario as completed
                                if self.current_scenario:
                                    self.current_scenario.is_completed = True
                                    self.current_scenario.success = False
                                break
                    
                    if not self.is_running:
                        break
                    
                    # Process input
                    if self.controller.process_input():
                        self.logger.log_info("Quitting simulation")
                        self.full_exit = True
                        break
                    
                    # Get current control state
                    current_control = self.vehicle_manager.vehicle.get_control()
                    
                    # Apply control if not in autopilot mode
                    if self.config.controller.type != 'autopilot':
                        control = self.controller.get_control()
                        self.vehicle_manager.apply_control(control)
                        current_control = control
                    
                    # Update vehicle state
                    self.vehicle_manager.update_state()
                    vehicle_state = self.vehicle_manager.state
                    
                    # Create display state
                    display_state = DisplayVehicleState(
                        speed=vehicle_state.speed,
                        position=vehicle_state.position,
                        heading=vehicle_state.heading,
                        distance_to_target=vehicle_state.distance_to_target,
                        controls={
                            'throttle': current_control.throttle,
                            'brake': current_control.brake,
                            'steer': current_control.steer,
                            'hand_brake': current_control.hand_brake,
                            'reverse': current_control.reverse,
                            'manual_gear_shift': current_control.manual_gear_shift,
                            'gear': current_control.gear
                        },
                        speed_kmh=vehicle_state.speed_kmh,
                        scenario_name=self.scenario_type.name.replace('_', ' ').title()
                    )
                    
                    # Update display
                    if not self.display_manager.render(
                        display_state,
                        self.world_manager.target.location
                    ):
                        self.logger.log_info("Display manager requested exit")
                        self.full_exit = True
                        break
                    
                    # Log simulation data
                    self._log_simulation_data(vehicle_state, current_control)
                    
                    # Check simulation end conditions
                    if self._should_end_simulation(vehicle_state):
                        self.logger.log_info("Simulation end conditions met")
                        break
                    
                    # Update scenario
                    if self.current_scenario:
                        self.current_scenario.update()
                        
                        # End simulation if scenario is completed
                        if self.current_scenario.is_completed:
                            if self.current_scenario.success:
                                self.logger.log_info("Scenario completed successfully!")
                            else:
                                self.logger.log_info("Scenario failed!")
                            # Set is_running to False to exit the loop
                            self.is_running = False
                            break
                    
                    # Tick the world
                    self.world_manager.world.tick()
                    
                except RuntimeError as e:
                    if "trying to operate on a destroyed actor" in str(e):
                        self.logger.log_error("Actor was destroyed, ending simulation...")
                        break
                    self.logger.log_error(f"Runtime error in simulation loop: {str(e)}")
                    raise
                except Exception as e:
                    self.logger.log_error(f"Unexpected error in simulation loop: {str(e)}")
                    raise
                
        except Exception as e:
            self.logger.log_error(f"Critical simulation error: {str(e)}")
            import traceback
            self.logger.log_error(f"Traceback: {traceback.format_exc()}")
            raise
        
        finally:
            try:
                if self.current_scenario:
                    self.current_scenario.cleanup()
                self.cleanup()
            except Exception as e:
                self.logger.log_error(f"Error during cleanup: {str(e)}")
                import traceback
                self.logger.log_error(f"Cleanup traceback: {traceback.format_exc()}")
            finally:
                # Don't exit here, let the main function handle the exit
                pygame.quit()

    def _log_simulation_data(self, vehicle_state, control) -> None:
        """Log current simulation data"""
        data = SimulationData(
            elapsed_time=time.time() - self.start_time,
            speed=vehicle_state.speed,
            position=vehicle_state.position,
            controls={
                'throttle': control.throttle,
                'brake': control.brake,
                'steer': control.steer,
                'hand_brake': control.hand_brake,
                'reverse': control.reverse,
                'manual_gear_shift': control.manual_gear_shift,
                'gear': control.gear
            },
            target_info={
                'distance': vehicle_state.distance_to_target,
                'heading': vehicle_state.heading_to_target,
                'heading_diff': vehicle_state.heading_difference
            },
            vehicle_state={
                'acceleration': vehicle_state.acceleration,
                'angular_velocity': vehicle_state.angular_velocity,
                'collision_intensity': vehicle_state.collision_intensity,
                'rotation': vehicle_state.rotation,
                'heading': vehicle_state.heading
            },
            weather=self.world_manager.get_weather_parameters(),
            traffic_count=len(self.world_manager.get_traffic_actors()),
            fps=self.display_manager.clock.get_fps(),
            event="",
            event_details=""
        )
        
        self.logger.log_data(data)
    
    def _should_end_simulation(self, vehicle_state) -> bool:
        """Check if simulation should end"""
        # Check time limit
        if time.time() - self.start_time > self.config.simulation.simulation_time:
            self.logger.log_info("Simulation time limit reached")
            return True
        
        # Check target reached - only if not in a scenario
        if not self.current_scenario and vehicle_state.distance_to_target < self.config.simulation.target_tolerance:
            self.logger.log_info("Target reached")
            return True
        
        # Check collision
        if vehicle_state.collision_intensity > self.config.simulation.max_collision_force:
            self.logger.log_error("Collision detected")
            return True
        
        return False
    
    def cleanup(self) -> None:
        """Clean up resources and reset world settings"""
        self.is_running = False
        
        try:
            # Clean up scenario first
            if self.current_scenario:
                self.current_scenario.cleanup()
                self.current_scenario = None
            
            # Clean up managers in reverse order of initialization
            if self.sensor_manager:
                self.sensor_manager.destroy()
                self.sensor_manager = None
            
            if self.vehicle_manager:
                self.vehicle_manager.destroy()
                self.vehicle_manager = None
            
            if self.world_manager:
                self.world_manager.cleanup()
                self.world_manager = None
            
            if self.display_manager:
                self.display_manager.cleanup()
                self.display_manager = None
            
            if self.logger:
                self.logger.close()
                self.logger = None
            
            # Force quit pygame
            pygame.quit()
            
        except Exception as e:
            print(f"Error during cleanup: {e}")
        finally:
            # Ensure we exit cleanly
            import sys
            if sys.platform == 'win32':
                import ctypes
                ctypes.windll.user32.PostQuitMessage(0)

def main():
    """Main entry point"""
    simulator = None
    logger = None
    
    try:
        # Add command line argument for scenario type
        import argparse
        parser = argparse.ArgumentParser(description='CARLA Simulator')
        parser.add_argument('--scenario', type=str, default='FOLLOW_ROUTE',
                          choices=[s.name for s in ScenarioType] + ['all'],
                          help='Type of scenario to run (use "all" to run all scenarios sequentially)')
        args = parser.parse_args()
        
        # Load configuration
        config_path = os.path.join(project_root, 'config', 'simulation.yaml')
        config = load_config(config_path)
        
        # Initialize logger first
        logger = SimulationLogger(config.logging)
        logger.log_info(f"Starting simulation with scenario: {args.scenario}")
        
        if args.scenario == 'all':
            # Get all scenario types
            all_scenarios = list(ScenarioType)
            total_scenarios = len(all_scenarios)
            logger.log_info(f"Total scenarios to run: {total_scenarios}")
            
            # Run all scenarios sequentially
            for i, scenario_type in enumerate(all_scenarios, 1):
                logger.log_info(f"\n{'='*50}")
                logger.log_info(f"Starting scenario {i}/{total_scenarios}: {scenario_type.name}")
                logger.log_info(f"{'='*50}\n")
                
                try:
                    # Create new simulator instance for each scenario
                    simulator = CarlaSimulator(config_path, scenario_type)
                    simulator.setup()
                    
                    # Run the scenario
                    try:
                        simulator.run()
                        # Check if full exit was requested
                        if hasattr(simulator, 'full_exit') and simulator.full_exit:
                            logger.log_info("Full exit requested, stopping all scenarios")
                            break
                        # If scenario quit was requested, continue to next scenario
                        elif hasattr(simulator, 'scenario_quit') and simulator.scenario_quit:
                            logger.log_info("Scenario quit requested, continuing to next scenario")
                            continue
                    except Exception as e:
                        logger.log_error(f"Error during scenario execution: {str(e)}")
                        import traceback
                        logger.log_error(f"Traceback: {traceback.format_exc()}")
                    finally:
                        # Always clean up the current scenario
                        if simulator:
                            try:
                                simulator.cleanup()
                            except Exception as e:
                                logger.log_error(f"Error during cleanup: {str(e)}")
                            finally:
                                simulator = None  # Reset simulator for next scenario
                    
                    # Small delay between scenarios
                    if i < total_scenarios:  # Don't wait after the last scenario
                        logger.log_info(f"Waiting 2 seconds before next scenario...")
                        time.sleep(2)
                        
                except Exception as e:
                    logger.log_error(f"Error in scenario {scenario_type.name}: {str(e)}")
                    import traceback
                    logger.log_error(f"Traceback: {traceback.format_exc()}")
                    if simulator:
                        try:
                            simulator.cleanup()
                        except Exception as cleanup_error:
                            logger.log_error(f"Cleanup error: {str(cleanup_error)}")
                        finally:
                            simulator = None
                    continue  # Continue to next scenario even if current one fails
                
            logger.log_info("\nAll scenarios completed!")
        else:
            # Run single scenario
            scenario_type = ScenarioType[args.scenario]
            logger.log_info(f"Running single scenario: {scenario_type.name}")
            simulator = CarlaSimulator(config_path, scenario_type)
            simulator.setup()
            simulator.run()
        
    except KeyboardInterrupt:
        if logger:
            logger.log_info("Simulation interrupted by user")
    except Exception as e:
        if logger:
            logger.log_error(f"Error during simulation: {str(e)}")
            import traceback
            logger.log_error(f"Traceback: {traceback.format_exc()}")
    finally:
        if simulator:
            try:
                simulator.cleanup()
            except Exception as e:
                if logger:
                    logger.log_error(f"Cleanup error: {str(e)}")
        pygame.quit()
        import sys
        sys.exit(0)

if __name__ == '__main__':
    main() 