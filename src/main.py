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
    FOLLOW_ROUTE = auto()
    AVOID_OBSTACLE = auto()
    EMERGENCY_BRAKE = auto()
    VEHICLE_CUTTING = auto()
    PEDESTRIAN_CROSSING = auto()

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
        
        print(f"Follow route scenario started with {self.num_waypoints} waypoints")

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
                print(f"Scenario completed successfully in {self.completion_time:.1f} seconds!")
            else:
                # Set next waypoint as target
                self.vehicle_manager.set_target(self.waypoints[self.current_waypoint])
                print(f"Reached waypoint {self.current_waypoint}/{len(self.waypoints)}")

class AvoidObstacleScenario(Scenario):
    """Scenario where vehicle must avoid static obstacles on the road"""
    def __init__(self, world_manager, vehicle_manager, num_obstacles=3):
        super().__init__(world_manager, vehicle_manager)
        self.num_obstacles = num_obstacles
        self.obstacles = []
        self.target_distance = 100.0  # meters
        self.obstacle_spacing = self.target_distance / (self.num_obstacles + 1)
        self.completion_distance = self.target_distance + 10.0

    def setup(self):
        # Get vehicle's current position and forward vector
        vehicle_transform = self.vehicle_manager.vehicle.get_transform()
        forward_vector = vehicle_transform.get_forward_vector()
        
        # Calculate target point straight ahead
        target_location = carla.Location(
            x=vehicle_transform.location.x + forward_vector.x * self.target_distance,
            y=vehicle_transform.location.y + forward_vector.y * self.target_distance,
            z=vehicle_transform.location.z
        )
        
        # Set the final target
        self.vehicle_manager.set_target(target_location)
        
        # Spawn obstacles along the path
        blueprint = self.world_manager.world.get_blueprint_library().find('static.prop.streetbarrier')
        for i in range(self.num_obstacles):
            distance = self.obstacle_spacing * (i + 1)
            # Add random offset to make it more challenging
            lateral_offset = random.uniform(-2.0, 2.0)
            
            obstacle_location = carla.Location(
                x=vehicle_transform.location.x + forward_vector.x * distance,
                y=vehicle_transform.location.y + forward_vector.y * distance + lateral_offset,
                z=vehicle_transform.location.z
            )
            
            obstacle_transform = carla.Transform(obstacle_location)
            obstacle = self.world_manager.world.spawn_actor(blueprint, obstacle_transform)
            self.obstacles.append(obstacle)
        
        self.start_time = time.time()
        print(f"Avoid obstacle scenario started with {self.num_obstacles} obstacles")

    def update(self):
        if self.is_completed:
            return

        # Get current vehicle state
        vehicle_location = self.vehicle_manager.vehicle.get_location()
        target_location = self.vehicle_manager.target
        
        # Check if vehicle has reached the target
        distance_to_target = vehicle_location.distance(target_location)
        
        # Check for collisions with obstacles
        for obstacle in self.obstacles:
            if vehicle_location.distance(obstacle.get_location()) < 1.0:
                self.is_completed = True
                self.success = False
                print("Failed: Collision with obstacle!")
                return
        
        # Check if passed all obstacles successfully
        if distance_to_target < 5.0:
            self.is_completed = True
            self.success = True
            self.completion_time = time.time() - self.start_time
            print(f"Successfully avoided all obstacles! Time: {self.completion_time:.1f} seconds")

    def cleanup(self):
        for obstacle in self.obstacles:
            if obstacle is not None:
                obstacle.destroy()
        self.obstacles = []

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
        print(f"Emergency brake scenario started. Target speed: {self.initial_speed} km/h")

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
            print("Obstacle spawned! Emergency brake required!")

        if self.obstacle_spawned:
            # Check distance to obstacle
            distance_to_obstacle = vehicle_transform.location.distance(self.obstacle.get_location())
            
            # Check if stopped safely
            if speed < 1.0 and distance_to_obstacle > self.safe_stop_distance:
                self.is_completed = True
                self.success = True
                self.completion_time = time.time() - self.start_time
                print(f"Successfully performed emergency brake! Time: {self.completion_time:.1f} seconds")
            elif distance_to_obstacle < self.safe_stop_distance:
                self.is_completed = True
                self.success = False
                print("Failed: Collision with obstacle!")

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

    def setup(self):
        # Get ego vehicle's transform
        ego_transform = self.vehicle_manager.vehicle.get_transform()
        forward_vector = ego_transform.get_forward_vector()
        right_vector = ego_transform.get_right_vector()
        
        # Calculate spawn point for cutting vehicle (to the right of ego vehicle)
        spawn_location = carla.Location(
            x=ego_transform.location.x + forward_vector.x * self.initial_distance + right_vector.x * 3.5,
            y=ego_transform.location.y + forward_vector.y * self.initial_distance + right_vector.y * 3.5,
            z=ego_transform.location.z
        )
        spawn_rotation = ego_transform.rotation
        spawn_transform = carla.Transform(spawn_location, spawn_rotation)
        
        # Spawn the cutting vehicle
        blueprint = self.world_manager.world.get_blueprint_library().find('vehicle.tesla.model3')
        blueprint.set_attribute('role_name', 'cutting_vehicle')
        self.cutting_vehicle = self.world_manager.world.spawn_actor(blueprint, spawn_transform)
        
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
        print("Vehicle cutting scenario started")

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
            print("Vehicle cutting in!")

        # Check for collision
        if distance < self.safe_distance:
            self.is_completed = True
            self.success = False
            print("Failed: Too close to cutting vehicle!")
            return
        
        # Check if cut is complete
        if self.is_cutting and not self.cut_complete and distance > self.cutting_distance:
            self.cut_complete = True
            print("Cut completed successfully!")
        
        # Check if scenario is complete (cut performed and safe distance maintained)
        if self.cut_complete and ego_speed > 0 and distance > self.safe_distance:
            self.is_completed = True
            self.success = True
            self.completion_time = time.time() - self.start_time
            print(f"Successfully handled vehicle cutting! Time: {self.completion_time:.1f} seconds")

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

    def setup(self):
        # Set initial speed for ego vehicle
        self.vehicle_manager.vehicle.set_target_velocity(
            carla.Vector3D(x=self.initial_speed/3.6, y=0.0, z=0.0)
        )
        
        # Get ego vehicle's transform
        ego_transform = self.vehicle_manager.vehicle.get_transform()
        forward_vector = ego_transform.get_forward_vector()
        right_vector = ego_transform.get_right_vector()
        
        # Calculate spawn point for pedestrian (on the sidewalk)
        spawn_location = carla.Location(
            x=ego_transform.location.x + forward_vector.x * self.crossing_distance + right_vector.x * 4.0,
            y=ego_transform.location.y + forward_vector.y * self.crossing_distance + right_vector.y * 4.0,
            z=ego_transform.location.z
        )
        spawn_rotation = ego_transform.rotation
        spawn_transform = carla.Transform(spawn_location, spawn_rotation)
        
        # Spawn the pedestrian
        blueprint = self.world_manager.world.get_blueprint_library().find('walker.pedestrian.0001')
        self.pedestrian = self.world_manager.world.spawn_actor(blueprint, spawn_transform)
        
        # Set target point far ahead for ego vehicle
        target_location = carla.Location(
            x=ego_transform.location.x + forward_vector.x * (self.crossing_distance + 100.0),
            y=ego_transform.location.y + forward_vector.y * (self.crossing_distance + 100.0),
            z=ego_transform.location.z
        )
        self.vehicle_manager.set_target(target_location)
        
        # Create and start walker AI controller
        walker_controller_bp = self.world_manager.world.get_blueprint_library().find('controller.ai.walker')
        self.controller = self.world_manager.world.spawn_actor(walker_controller_bp, carla.Transform(), self.pedestrian)
        
        self.start_time = time.time()
        print("Pedestrian crossing scenario started")

    def update(self):
        if self.is_completed:
            return

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
            print("Pedestrian starting to cross!")

        # Check for collision
        if distance < self.safe_distance:
            self.is_completed = True
            self.success = False
            print("Failed: Too close to pedestrian!")
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
                print("Pedestrian crossed successfully!")
        
        # Check if scenario is complete (crossing performed and safe distance maintained)
        if self.cross_complete and ego_speed > 0 and distance > self.safe_distance:
            self.is_completed = True
            self.success = True
            self.completion_time = time.time() - self.start_time
            print(f"Successfully handled pedestrian crossing! Time: {self.completion_time:.1f} seconds")

    def cleanup(self):
        if self.controller is not None:
            self.controller.stop()
            self.controller.destroy()
        if self.pedestrian is not None:
            self.pedestrian.destroy()

def find_available_tm_port(client):
    """Find an available Traffic Manager port using random ports"""
    base_port = 8000
    max_attempts = 20
    
    ports_to_try = random.sample(range(base_port, base_port + 1000), max_attempts)
    
    for port in ports_to_try:
        try:
            tm = client.get_trafficmanager(port)
            tm.set_synchronous_mode(True)
            print(f"Using Traffic Manager port: {port}")
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
        
        # Connect to CARLA server with retries
        max_retries = 3
        retry_delay = 5  # seconds
        
        for attempt in range(max_retries):
            try:
                print(f"Attempting to connect to CARLA server at {self.config.server.host}:{self.config.server.port} (attempt {attempt + 1}/{max_retries})...")
                self.client = carla.Client(self.config.server.host, self.config.server.port)
                self.client.set_timeout(self.config.server.timeout)
                
                # Test connection
                self.client.get_world()
                print("Successfully connected to CARLA server")
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"Connection failed: {str(e)}")
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    print("\nFailed to connect after multiple attempts.")
                    print("Please check the following:")
                    print(f"1. Is the CARLA server running at {self.config.server.host}:{self.config.server.port}?")
                    print("2. Is the server accessible from your network?")
                    print("3. Are there any firewall rules blocking the connection?")
                    print("4. Is the server running on a different port?")
                    raise
        
        # Initialize components
        self.world_manager = None
        self.vehicle_manager = None
        self.sensor_manager = None
        self.display_manager = None
        self.controller = None
        
        # Initialize state
        self.is_running = False
        self.start_time = None
        self.current_scenario = None
    
    def setup(self) -> None:
        """Set up simulation components"""
        try:
            # Get world and apply settings
            world = self.client.get_world()
            
            # Set up synchronous mode first
            settings = world.get_settings()
            settings.synchronous_mode = True
            settings.fixed_delta_seconds = 1.0 / self.config.simulation.update_rate
            world.apply_settings(settings)
            
            # Initialize managers
            self.world_manager = WorldManager(self.client, self.config.world)
            self.vehicle_manager = VehicleManager(world, self.config.vehicle_model)
            
            # Spawn vehicle
            spawn_point = self.world_manager.get_random_spawn_point()
            self.vehicle_manager.spawn_vehicle(spawn_point)
            
            # Set up autopilot if enabled
            if self.config.controller.type == 'autopilot':
                # Find available Traffic Manager port
                tm_port = find_available_tm_port(self.client)
                traffic_manager = self.client.get_trafficmanager(tm_port)
                traffic_manager.set_synchronous_mode(True)
                
                # Enable autopilot with traffic manager port
                self.vehicle_manager.vehicle.set_autopilot(True, tm_port)
                
                # Configure vehicle behavior
                traffic_manager.set_global_distance_to_leading_vehicle(2.5)
                traffic_manager.vehicle_percentage_speed_difference(self.vehicle_manager.vehicle, 0)  # No speed reduction
                traffic_manager.ignore_lights_percentage(self.vehicle_manager.vehicle, 100)
                traffic_manager.ignore_signs_percentage(self.vehicle_manager.vehicle, 100)
                traffic_manager.auto_lane_change(self.vehicle_manager.vehicle, True)
                traffic_manager.random_left_lanechange_percentage(self.vehicle_manager.vehicle, 0)
                traffic_manager.random_right_lanechange_percentage(self.vehicle_manager.vehicle, 0)
                traffic_manager.set_desired_speed(self.vehicle_manager.vehicle, self.config.simulation.max_speed)
                
                print("Autopilot enabled with maximum speed settings")
            
            # Generate target point
            target = self.world_manager.generate_target_point(spawn_point)
            self.vehicle_manager.set_target(target.location)
            
            # Initialize sensors
            self.sensor_manager = SensorManager(self.vehicle_manager.vehicle, self.config.sensors)
            
            # Initialize display
            self.display_manager = DisplayManager(self.config.display)
            
            # Add camera view as sensor observer
            self.sensor_manager.add_observer('camera', self.display_manager.camera_view)
            
            # Initialize controller
            self.controller = VehicleController(self.config.controller)
            
            # Set control strategy based on configuration
            if self.config.controller.type == 'keyboard':
                self.controller.set_strategy(KeyboardController(self.config.controller))
            elif self.config.controller.type == 'gamepad':
                self.controller.set_strategy(GamepadController(self.config.controller))
            elif self.config.controller.type == 'autopilot':
                self.controller.set_strategy(AutopilotController(self.vehicle_manager.vehicle, self.config.controller, self.client))
            else:
                raise ValueError(f"Unknown controller type: {self.config.controller.type}")
            
            # Setup scenario using the specified type
            self.setup_scenario(self.scenario_type)
            
        except Exception as e:
            self.logger.log_error(f"Failed to setup simulation: {str(e)}")
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
            
            while self.is_running:
                try:
                    # Process input
                    if self.controller.process_input():
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
                        break
                    
                    # Log simulation data
                    self._log_simulation_data(vehicle_state, current_control)
                    
                    # Check simulation end conditions
                    if self._should_end_simulation(vehicle_state):
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
                            break
                    
                    # Tick the world
                    self.world_manager.world.tick()
                    
                except RuntimeError as e:
                    if "trying to operate on a destroyed actor" in str(e):
                        print("Actor was destroyed, ending simulation...")
                        break
                    raise
                
        except Exception as e:
            self.logger.log_error(f"Simulation error: {str(e)}")
            raise
        
        finally:
            try:
                if self.current_scenario:
                    self.current_scenario.cleanup()
                self.cleanup()
            except Exception as e:
                print(f"Error during cleanup: {e}")
            finally:
                # Force exit the process
                import os
                os._exit(0)
    
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
            return True
        
        # Check target reached
        if vehicle_state.distance_to_target < self.config.simulation.target_tolerance:
            return True
        
        # Check collision
        if vehicle_state.collision_intensity > self.config.simulation.max_collision_force:
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
    try:
        # Add command line argument for scenario type
        import argparse
        parser = argparse.ArgumentParser(description='CARLA Simulator')
        parser.add_argument('--scenario', type=str, default='FOLLOW_ROUTE',
                          choices=[s.name for s in ScenarioType],
                          help='Type of scenario to run')
        args = parser.parse_args()
        
        # Convert string scenario type to enum
        scenario_type = ScenarioType[args.scenario]
        
        # Load configuration
        config_path = os.path.join(project_root, 'config', 'simulation.yaml')
        
        # Create and run simulator with specified scenario
        simulator = CarlaSimulator(config_path, scenario_type)
        simulator.setup()
        simulator.run()
        
    except KeyboardInterrupt:
        print("\nSimulation interrupted by user")
    except Exception as e:
        print(f"Error: {str(e)}")
        raise
    finally:
        pygame.quit()

if __name__ == '__main__':
    main() 