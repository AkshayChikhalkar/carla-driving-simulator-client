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
from .default_config import SIMULATION_CONFIG
from .paths import get_project_root

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

class Logger:
    """Manages logging configuration and setup"""
    
    _instance: Optional['Logger'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        # Get configuration values with fallbacks
        self.log_level = getattr(SIMULATION_CONFIG, 'log_level', 'INFO')
        self.log_dir = get_project_root() / 'logs'
        self.log_format = getattr(SIMULATION_CONFIG, 'log_format', 
            '%(asctime)s - %(levelname)s - %(message)s')
        self.log_date_format = getattr(SIMULATION_CONFIG, 'log_date_format', 
            '%Y-%m-%d %H:%M:%S')
        self.log_to_file = getattr(SIMULATION_CONFIG, 'log_to_file', True)
        self.log_to_console = getattr(SIMULATION_CONFIG, 'log_to_console', True)
        
        # Initialize CSV logging attributes
        self.csv_file = None
        self.csv_writer = None
        
        self._setup_logging()
        self._initialized = True
        
    def _setup_logging(self) -> None:
        """Setup logging configuration"""
        try:
            # Create log directory if it doesn't exist
            os.makedirs(self.log_dir, exist_ok=True)
            
            # Generate log filename with current date
            current_date = datetime.now().strftime('%Y%m%d')
            log_file = self.log_dir / f'simulation_{current_date}.log'
            
            # Configure root logger
            handlers = []
            
            if self.log_to_file:
                # Use buffered file handler with 8KB buffer
                file_handler = logging.FileHandler(str(log_file), mode='a', encoding='utf-8')
                file_handler.setLevel(self.log_level)
                handlers.append(file_handler)
                
            if self.log_to_console:
                handlers.append(logging.StreamHandler())
                
            # Configure logging format
            formatter = logging.Formatter(
                fmt=self.log_format,
                datefmt=self.log_date_format
            )
            
            # Apply formatter to all handlers
            for handler in handlers:
                handler.setFormatter(formatter)
                
            # Configure root logger
            logging.basicConfig(
                level=self.log_level,
                handlers=handlers
            )
            
            # Create logger instance
            self.logger = logging.getLogger(__name__)
            self.logger.info("Logging system initialized")
            
            # Setup CSV logging if enabled
            if self.log_to_file:
                csv_file = log_file.with_suffix('.csv')
                # Check if CSV file exists to determine if we need to write header
                file_exists = os.path.exists(csv_file)
                # Use buffered I/O with 8KB buffer
                self.csv_file = open(csv_file, 'a', newline='', buffering=8192)
                self.csv_writer = csv.writer(self.csv_file)
                if not file_exists:
                    self._write_csv_header()
            
        except Exception as e:
            print(f"Error setting up logging: {str(e)}")
            raise
            
    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger instance for the specified name"""
        logger = logging.getLogger(name)
        # Remove the src.utils.logging prefix from the logger name
        logger.name = name.split('.')[-1]
        return logger
        
    def set_level(self, level: str) -> None:
        """Set the logging level"""
        try:
            logging.getLogger().setLevel(level)
            self.logger.info(f"Logging level set to {level}")
        except Exception as e:
            self.logger.error(f"Error setting log level: {str(e)}")
            raise
    
    def _write_csv_header(self) -> None:
        """Write CSV header"""
        if not self.csv_writer:
            return
            
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
        if not self.csv_writer:
            return
            
        try:
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
            # Only flush periodically (every 100 rows) to reduce I/O operations
            if not hasattr(self, '_row_count'):
                self._row_count = 0
            self._row_count += 1
            if self._row_count % 100 == 0:
                self.csv_file.flush()
        except Exception as e:
            self.logger.error(f"Error writing to CSV: {str(e)}")
    
    def log_event(self, elapsed_time: float, event: str, details: str) -> None:
        """Log significant events to operations log"""
        self.logger.info(f"[{elapsed_time:.1f}s] {event}: {details}")
    
    def close(self) -> None:
        """Close all log files"""
        self.logger.info("")  # Empty line for readability
        self.logger.info(f"Simulation ended at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        if self.csv_file:
            try:
                self.csv_file.close()
            except Exception as e:
                self.logger.error(f"Error closing CSV file: {str(e)}") 