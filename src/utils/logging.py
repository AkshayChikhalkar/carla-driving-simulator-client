"""
Logging system for the CARLA Driving Simulator.
"""

import os
import logging
import traceback
import csv
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Any, Dict, TextIO
from pathlib import Path
from .settings import DEBUG_MODE

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

# Default configuration
DEFAULT_CONFIG = {
    'log_dir': 'logs',
    'log_level': 'INFO',
    'log_to_file': True,
    'log_to_console': True
}

class Logger:
    """Logger class for the CARLA Driving Simulator"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the logger if not already initialized"""
        if not self._initialized:
            self._setup_logger()
            self._initialized = True
    
    def _setup_logger(self):
        """Setup the logger with default configuration"""
        # Get project root directory
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # Setup log directory
        log_dir = os.path.join(project_root, DEFAULT_CONFIG['log_dir'])
        os.makedirs(log_dir, exist_ok=True)
        
        # Create logger
        self.logger = logging.getLogger('carla_simulator')
        self.logger.setLevel('DEBUG' if DEBUG_MODE else 'INFO')
        
        # Create formatters
        file_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        console_formatter = logging.Formatter(
            '%(levelname)s: %(message)s'
        )
        
        # Add file handler if enabled
        if DEFAULT_CONFIG['log_to_file']:
            # Create daily log file
            current_date = datetime.now().strftime("%Y%m%d")
            log_file = os.path.join(
                log_dir,
                f'simulation_{current_date}.log'
            )
            
            # Check if file exists and append if it does
            file_handler = logging.FileHandler(log_file, mode='a')
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
            
            # Setup CSV logging with daily file
            csv_file = log_file.replace('.log', '.csv')
            # Check if CSV file exists to determine if we need to write header
            file_exists = os.path.exists(csv_file)
            self.csv_file = open(csv_file, 'a', newline='')
            self.csv_writer = csv.writer(self.csv_file)
            
            # Write header only if file is new
            if not file_exists:
                self._write_csv_header()
        
        # Add console handler if enabled
        if DEFAULT_CONFIG['log_to_console']:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)
            
        # Write header to operations log only if it's a new file
        if not os.path.exists(log_file) or os.path.getsize(log_file) == 0:
            self.logger.info("=== CARLA Simulation Operational Log ===")
            self.logger.info(f"Simulation started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self.logger.info("=" * 50)
            self.logger.info("")  # Empty line for readability
    
    def _write_csv_header(self) -> None:
        """Write CSV header"""
        header = [
            'elapsed_time', 'speed', 'position_x', 'position_y', 'position_z',
            'throttle', 'brake', 'steer', 'target_distance', 'target_heading',
            'vehicle_heading', 'heading_diff', 'acceleration', 'angular_velocity',
            'gear', 'hand_brake', 'reverse', 'manual_gear_shift',
            'collision_intensity', 'cloudiness', 'precipitation', 'traffic_count',
            'fps', 'event', 'event_details', 'rotation_x', 'rotation_y', 'rotation_z'
        ]
        self.csv_writer.writerow(header)
        self.csv_file.flush()
    
    def set_debug_mode(self, enabled: bool):
        """Set debug mode"""
        global DEBUG_MODE
        DEBUG_MODE = enabled
        self.logger.setLevel('DEBUG' if enabled else 'INFO')
    
    def info(self, message: str):
        """Log info message"""
        self.logger.info(message)
    
    def error(self, message: str, exc_info: Optional[Exception] = None):
        """Log error message with optional exception info"""
        if exc_info and DEBUG_MODE:
            self.logger.error(f"{message}\n{traceback.format_exc()}")
        else:
            self.logger.error(message)
    
    def warning(self, message: str):
        """Log warning message"""
        self.logger.warning(message)
    
    def debug(self, message: str):
        """Log debug message (only shown in debug mode)"""
        if DEBUG_MODE:
            self.logger.debug(message)
    
    def log_vehicle_state(self, state: Dict[str, Any]):
        """Log vehicle state (only shown in debug mode)"""
        if DEBUG_MODE:
            self.logger.debug(f"Vehicle State: {state}")
            
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
        self.logger.info(f"[{elapsed_time:.1f}s] {event}: {details}")
    
    def close(self) -> None:
        """Close all log files"""
        self.logger.info("")  # Empty line for readability
        self.logger.info(f"Simulation ended at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        if hasattr(self, 'csv_file'):
            self.csv_file.close() 