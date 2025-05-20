"""
Logging utilities for the simulation.
"""

import logging
import csv
import datetime
import os
from dataclasses import dataclass
from typing import Dict, Any, TextIO
from .config import LoggingConfig

@dataclass
class SimulationData:
    """Data structure for simulation metrics"""
    elapsed_time: float
    speed: float
    position: tuple[float, float, float]
    controls: Dict[str, float]
    target_info: Dict[str, float]
    vehicle_state: Dict[str, Any]
    weather: Dict[str, float]
    traffic_count: int
    fps: float
    event: str
    event_details: str

class SimulationLogger:
    """Handles logging of simulation data and events"""
    
    def __init__(self, config: LoggingConfig):
        """Initialize loggers"""
        self.config = config
        
        # Ensure logs directory exists
        log_dir = os.path.dirname(config.simulation_file)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # Setup CSV logging
        self.csv_file = open(config.simulation_file, 'w', newline='')
        self.csv_writer = csv.writer(self.csv_file)
        self._write_csv_header()
        
        # Setup operations logging
        self.op_file = open(config.operations_file, 'w')
        self._write_op_header()
        
        # Setup application logging
        self.logger = logging.getLogger('simulation')
        self.logger.setLevel(getattr(logging, config.log_level.upper()))
    
    def _write_csv_header(self) -> None:
        """Write CSV file header"""
        self.csv_writer.writerow([
            "Time_Elapsed[s]", "Speed[km/h]", 
            "Position_X[m]", "Position_Y[m]", "Position_Z[m]",
            "Throttle[0-1]", "Brake[0-1]", "Steer[-1to1]",
            "Distance_To_Target[m]", "Heading_To_Target[deg]",
            "Vehicle_Heading[deg]", "Heading_Difference[deg]",
            "Acceleration[m/s2]", "Angular_Velocity[rad/s]",
            "Gear", "HandBrake[0/1]", "Reverse[0/1]",
            "Manual_Gear_Shift[0/1]", "Collision_Intensity[N]",
            "Weather_Cloudiness[%]", "Weather_Precipitation[%]",
            "Traffic_Count", "FPS[Hz]", "Scenario_Event",
            "Event_Details", "Rotation_Pitch[deg]",
            "Rotation_Yaw[deg]", "Rotation_Roll[deg]"
        ])
    
    def _write_op_header(self) -> None:
        """Write operations log header"""
        self.op_file.write("=== CARLA Simulation Operational Log ===\n")
        self.op_file.write(f"Simulation started at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        self.op_file.write("=" * 50 + "\n\n")
    
    def log_data(self, data: SimulationData) -> None:
        """Log simulation data to CSV file"""
        self.csv_writer.writerow([
            f"{data.elapsed_time:.2f}",
            f"{data.speed * 3.6:.2f}",  # Convert m/s to km/h
            f"{data.position[0]:.2f}",
            f"{data.position[1]:.2f}",
            f"{data.position[2]:.2f}",
            f"{data.controls['throttle']:.2f}",
            f"{data.controls['brake']:.2f}",
            f"{data.controls['steer']:.2f}",
            f"{data.target_info['distance']:.2f}",
            f"{data.target_info['heading']:.2f}",
            f"{data.vehicle_state['heading']:.2f}",
            f"{data.target_info['heading_diff']:.2f}",
            f"{data.vehicle_state['acceleration']:.2f}",
            f"{data.vehicle_state['angular_velocity']:.2f}",
            data.controls['gear'],
            1 if data.controls['hand_brake'] else 0,
            1 if data.controls['reverse'] else 0,
            1 if data.controls['manual_gear_shift'] else 0,
            f"{data.vehicle_state['collision_intensity']:.2f}",
            f"{data.weather['cloudiness']:.2f}",
            f"{data.weather['precipitation']:.2f}",
            data.traffic_count,
            f"{data.fps:.1f}",
            data.event,
            data.event_details,
            f"{data.vehicle_state['rotation'][0]:.2f}",
            f"{data.vehicle_state['rotation'][1]:.2f}",
            f"{data.vehicle_state['rotation'][2]:.2f}"
        ])
        self.csv_file.flush()
    
    def log_event(self, elapsed_time: float, event: str, details: str) -> None:
        """Log significant events to operations log"""
        self.op_file.write(f"[{elapsed_time:.1f}s] {event}: {details}\n")
        self.op_file.flush()
    
    def log_error(self, message: str) -> None:
        """Log error messages"""
        self.logger.error(message)
        self.op_file.write(f"ERROR: {message}\n")
        self.op_file.flush()
    
    def log_info(self, message: str) -> None:
        """Log informational messages"""
        self.logger.info(message)
        self.op_file.write(f"INFO: {message}\n")
        self.op_file.flush()
    
    def close(self) -> None:
        """Close all log files"""
        self.csv_file.close()
        self.op_file.write(f"\nSimulation ended at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        self.op_file.close()

def setup_logger(config: LoggingConfig) -> logging.Logger:
    """Set up application logger"""
    logger = logging.getLogger('simulation')
    logger.setLevel(getattr(logging, config.log_level.upper()))
    
    # Add console handler
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger 