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

class CollisionSensor(SensorSubject):
    """Collision detection sensor"""
    
    def __init__(self, vehicle: carla.Vehicle, config: Dict[str, Any]):
        super().__init__()
        self.vehicle = vehicle
        self.config = config
        world = self.vehicle.get_world()
        
        # Create collision sensor
        bp = world.get_blueprint_library().find('sensor.other.collision')
        self.sensor = world.spawn_actor(bp, carla.Transform(), attach_to=vehicle)
        
        # Weak reference to avoid circular reference
        weak_self = weakref.ref(self)
        self.sensor.listen(lambda event: CollisionSensor._on_collision(weak_self, event))
    
    @staticmethod
    def _on_collision(weak_self: weakref.ReferenceType, event: carla.CollisionEvent) -> None:
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
            intensity=intensity
        )
        
        # Notify observers
        self.notify(data)
    
    def destroy(self) -> None:
        """Clean up the sensor"""
        if self.sensor is not None:
            self.sensor.destroy()

class CameraSensor(SensorSubject):
    """Camera sensor"""
    
    def __init__(self, vehicle: carla.Vehicle, config: Dict[str, Any]):
        super().__init__()
        self.vehicle = vehicle
        self.config = config
        world = self.vehicle.get_world()
        
        # Create camera sensor
        bp = world.get_blueprint_library().find('sensor.camera.rgb')
        bp.set_attribute('image_size_x', str(config['width']))
        bp.set_attribute('image_size_y', str(config['height']))
        bp.set_attribute('fov', str(config['fov']))
        
        # Spawn the camera
        spawn_point = carla.Transform(
            carla.Location(x=config['x'], y=config['y'], z=config['z']),
            carla.Rotation(pitch=-15)  # Tilt camera down slightly
        )
        self.sensor = world.spawn_actor(bp, spawn_point, attach_to=vehicle)
        
        # Weak reference to avoid circular reference
        weak_self = weakref.ref(self)
        self.sensor.listen(lambda image: CameraSensor._on_image(weak_self, image))
    
    @staticmethod
    def _on_image(weak_self: weakref.ReferenceType, image: carla.Image) -> None:
        """Image callback"""
        self = weak_self()
        if not self:
            return
        
        try:
            # Convert image to numpy array
            array = np.frombuffer(image.raw_data, dtype=np.dtype("uint8"))
            array = np.reshape(array, (image.height, image.width, 4))
            array = array[:, :, :3]  # Remove alpha channel
            
            # Create camera data
            data = CameraData(
                frame=image.frame,
                timestamp=image.timestamp,
                transform=image.transform,
                image=array,
                width=image.width,
                height=image.height
            )
            
            # Notify observers
            self.notify(data)
        except Exception as e:
            print(f"Error processing camera image: {e}")
    
    def destroy(self) -> None:
        """Clean up the sensor"""
        if self.sensor is not None:
            self.sensor.destroy()

class GNSSSensor(SensorSubject):
    """GNSS (GPS) sensor"""
    
    def __init__(self, vehicle: carla.Vehicle, config: Dict[str, Any]):
        super().__init__()
        self.vehicle = vehicle
        self.config = config
        world = self.vehicle.get_world()
        
        # Create GNSS sensor
        bp = world.get_blueprint_library().find('sensor.other.gnss')
        self.sensor = world.spawn_actor(bp, carla.Transform(carla.Location(x=0.0, z=0.0)), attach_to=vehicle)
        
        # Weak reference to avoid circular reference
        weak_self = weakref.ref(self)
        self.sensor.listen(lambda event: GNSSSensor._on_gnss_data(weak_self, event))
    
    @staticmethod
    def _on_gnss_data(weak_self: weakref.ReferenceType, event: carla.GnssMeasurement) -> None:
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
            altitude=event.altitude
        )
        
        # Notify observers
        self.notify(data)
    
    def destroy(self) -> None:
        """Clean up the sensor"""
        if self.sensor is not None:
            self.sensor.destroy()

class SensorManager:
    """Manages all vehicle sensors"""
    
    def __init__(self, vehicle: carla.Vehicle, config: SensorConfig):
        """Initialize sensor manager with vehicle and configuration"""
        self.vehicle = vehicle
        self.config = config
        self.sensors: Dict[str, SensorSubject] = {}
        
        print("Initializing sensor manager...")
        
        # Initialize collision sensor
        if config.collision.enabled:
            print("Setting up collision sensor...")
            self.sensors['collision'] = CollisionSensor(vehicle, {})
        
        # Initialize camera sensor
        if config.camera.enabled:
            print("Setting up camera sensor...")
            camera_config = {
                'width': config.camera.width,
                'height': config.camera.height,
                'fov': config.camera.fov,
                'x': config.camera.x,
                'y': config.camera.y,
                'z': config.camera.z
            }
            self.sensors['camera'] = CameraSensor(vehicle, camera_config)
            print("Camera sensor setup complete")
        
        # Initialize GNSS sensor
        if config.gnss.enabled:
            print("Setting up GNSS sensor...")
            self.sensors['gnss'] = GNSSSensor(vehicle, {})
    
    def add_observer(self, sensor_type: str, observer: SensorObserver) -> None:
        """Add an observer to a specific sensor"""
        if sensor_type in self.sensors:
            print(f"Adding observer to {sensor_type} sensor")
            self.sensors[sensor_type].attach(observer)
        else:
            print(f"Warning: Attempted to add observer to non-existent sensor: {sensor_type}")
    
    def remove_observer(self, sensor_type: str, observer: SensorObserver) -> None:
        """Remove an observer from a specific sensor"""
        if sensor_type in self.sensors:
            self.sensors[sensor_type].detach(observer)
    
    def get_sensor(self, sensor_type: str) -> Optional[SensorSubject]:
        """Get a specific sensor by type"""
        return self.sensors.get(sensor_type)
    
    def destroy(self) -> None:
        """Clean up all sensors"""
        for sensor in self.sensors.values():
            sensor.destroy()
        self.sensors.clear() 