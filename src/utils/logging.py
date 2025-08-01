"""
Logging system for the CARLA Driving Simulator.
"""

import os
import logging
import traceback
from datetime import datetime
from typing import Optional, Any, Dict
from pathlib import Path

from src.models.metrics import SimulationMetricsData
from .settings import DEBUG_MODE
from .default_config import SIMULATION_CONFIG
from .paths import get_project_root
from .types import SimulationData
from src.database.config import SessionLocal
from src.database.models import SimulationMetrics
import uuid


class Logger:
    """Manages logging configuration and setup"""

    _instance: Optional["Logger"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # Get configuration values with fallbacks
        self.log_level = getattr(SIMULATION_CONFIG, "log_level", "INFO")
        self.log_dir = get_project_root() / "logs"
        self.log_format = getattr(
            SIMULATION_CONFIG, "log_format", "%(asctime)s - %(levelname)s - %(message)s"
        )
        self.log_date_format = getattr(
            SIMULATION_CONFIG, "log_date_format", "%Y-%m-%d %H:%M:%S"
        )
        self.log_to_file = True
        self.log_to_console = getattr(SIMULATION_CONFIG, "log_to_console", True)

        self._setup_logging()
        self._initialized = True

    def _setup_logging(self) -> None:
        """Setup logging configuration"""
        try:
            # Create log directory if it doesn't exist
            os.makedirs(self.log_dir, exist_ok=True)

            # Generate log filename with current date
            current_date = datetime.now().strftime("%Y%m%d")
            log_file = self.log_dir / f"simulation_{current_date}.log"

            # Configure root logger
            handlers = []

            if self.log_to_file:
                # Use buffered file handler with 8KB buffer
                file_handler = logging.FileHandler(
                    str(log_file), mode="a", encoding="utf-8"
                )
                file_handler.setLevel(self.log_level)
                handlers.append(file_handler)

            if self.log_to_console:
                handlers.append(logging.StreamHandler())

            # Configure logging format
            formatter = logging.Formatter(
                fmt=self.log_format, datefmt=self.log_date_format
            )

            # Apply formatter to all handlers
            for handler in handlers:
                handler.setFormatter(formatter)

            # Configure root logger
            logging.basicConfig(level=self.log_level, handlers=handlers)

            # Create logger instance
            self.logger = logging.getLogger(__name__)

        except Exception as e:
            print(f"Error setting up logging: {str(e)}")
            raise

    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger instance for the specified name"""
        logger = logging.getLogger(name)
        # Remove the src.utils.logging prefix from the logger name
        logger.name = name.split(".")[-1]
        return logger

    def set_level(self, level: str) -> None:
        """Set the logging level"""
        try:
            logging.getLogger().setLevel(level)
            self.logger.info(f"Logging level set to {level}")
        except Exception as e:
            self.logger.error(f"Error setting log level: {str(e)}")
            raise

    def set_debug_mode(self, enabled: bool):
        """Set debug mode"""
        global DEBUG_MODE
        DEBUG_MODE = enabled
        self.logger.setLevel("DEBUG" if enabled else "INFO")

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

    def critical(self, message: str, exc_info: Optional[Exception] = None):
        """Log critical message with optional exception info"""
        if exc_info and DEBUG_MODE:
            self.logger.critical(f"{message}\n{traceback.format_exc()}")
        else:
            self.logger.critical(message)

    def log_vehicle_state(self, state: Dict[str, Any]):
        """Log vehicle state (only shown in debug mode)"""
        if DEBUG_MODE:
            self.logger.debug(f"Vehicle State: {state}")

    def set_scenario_id(self, scenario_id: int):
        """Set the current simulation/session id for DB logging."""
        self._scenario_id = scenario_id

    def set_session_id(self, session_id):
        # Accept both string and UUID, but always store as UUID
        if isinstance(session_id, str):
            session_id = uuid.UUID(session_id)
        self._session_id = session_id
        self.logger.info(f"Session ID set to: {session_id}")

    def log_data(self, data: SimulationData) -> None:
        """Log simulation data to PostgreSQL database"""
        try:
            db = SessionLocal()
            metrics_data = SimulationMetricsData.from_simulation_data(
                data,
                scenario_id=getattr(self, "_scenario_id", None),
                session_id=getattr(self, "_session_id", None),
            )
            db_metrics = SimulationMetrics.from_metrics_data(metrics_data)
            db.add(db_metrics)
            db.commit()
            db.close()
        except Exception as e:
            self.logger.error(f"Error writing to DB: {str(e)}")

    def log_event(self, elapsed_time: float, event: str, details: str) -> None:
        """Log significant events to operations log"""
        self.logger.info(f"[{elapsed_time:.1f}s] {event}: {details}")

    def close(self) -> None:
        """Close logging system"""
        self.logger.info("")  # Empty line for readability
        self.logger.info(
            f"Simulation ended at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
