import os
import json
from datetime import datetime
from typing import Dict, Any
from src.core.interfaces import ILogger
from src.utils.config import LoggingConfig

class SimulationLogger(ILogger):
    """Logs simulation events and data"""
    def __init__(self, config: LoggingConfig):
        self.config = config
        self.simulation_log = None
        self.operations_log = None
        self._setup_logging()

    def _setup_logging(self) -> None:
        """Setup logging files and handlers"""
        if not self.config.enabled:
            return

        # Create logs directory if it doesn't exist
        os.makedirs(self.config.directory, exist_ok=True)

        # Setup simulation log
        sim_log_path = os.path.join(self.config.directory, self.config.simulation_file)
        self.simulation_log = open(sim_log_path, 'w')
        self.simulation_log.write("timestamp,event_type,data\n")

        # Setup operations log
        ops_log_path = os.path.join(self.config.directory, self.config.operations_file)
        self.operations_log = open(ops_log_path, 'w')
        self.operations_log.write("timestamp,operation,status,details\n")

    def log_info(self, message: str) -> None:
        """Log informational message"""
        if not self.config.enabled:
            return
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[INFO] {message}")
        if self.operations_log:
            self.operations_log.write(f"{timestamp},info,success,{message}\n")
            self.operations_log.flush()

    def log_error(self, message: str) -> None:
        """Log error message"""
        if not self.config.enabled:
            return
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[ERROR] {message}")
        if self.operations_log:
            self.operations_log.write(f"{timestamp},error,failure,{message}\n")
            self.operations_log.flush()

    def log_warning(self, message: str) -> None:
        """Log warning message"""
        if not self.config.enabled:
            return
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[WARNING] {message}")
        if self.operations_log:
            self.operations_log.write(f"{timestamp},warning,success,{message}\n")
            self.operations_log.flush()

    def log_vehicle_state(self, state: Dict[str, Any]) -> None:
        """Log vehicle state data"""
        if not self.config.enabled or not self.simulation_log:
            return
            
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        
        # Extract relevant vehicle state data
        state_data = {
            'location': {
                'x': state.get('location', {}).get('x', 0.0),
                'y': state.get('location', {}).get('y', 0.0),
                'z': state.get('location', {}).get('z', 0.0)
            },
            'rotation': {
                'pitch': state.get('rotation', {}).get('pitch', 0.0),
                'yaw': state.get('rotation', {}).get('yaw', 0.0),
                'roll': state.get('rotation', {}).get('roll', 0.0)
            },
            'velocity': {
                'x': state.get('velocity', {}).get('x', 0.0),
                'y': state.get('velocity', {}).get('y', 0.0),
                'z': state.get('velocity', {}).get('z', 0.0)
            },
            'acceleration': {
                'x': state.get('acceleration', {}).get('x', 0.0),
                'y': state.get('acceleration', {}).get('y', 0.0),
                'z': state.get('acceleration', {}).get('z', 0.0)
            },
            'control': {
                'throttle': state.get('control', {}).get('throttle', 0.0),
                'steer': state.get('control', {}).get('steer', 0.0),
                'brake': state.get('control', {}).get('brake', 0.0),
                'hand_brake': state.get('control', {}).get('hand_brake', False),
                'reverse': state.get('control', {}).get('reverse', False)
            }
        }
        
        # Write to simulation log
        self.simulation_log.write(f"{timestamp},vehicle_state,{json.dumps(state_data)}\n")
        self.simulation_log.flush()

    def cleanup(self) -> None:
        """Cleanup logging resources"""
        if self.simulation_log:
            self.simulation_log.close()
        if self.operations_log:
            self.operations_log.close() 