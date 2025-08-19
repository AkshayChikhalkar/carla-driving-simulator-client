"""
Web display manager that extends the base display manager for web streaming.
"""

from typing import Optional
import numpy as np
from .display_manager import DisplayManager, VehicleState
import carla
import pygame


class WebDisplayManager(DisplayManager):
    """Extended display manager for web streaming"""

    def __init__(self, config):
        """Initialize web display manager"""
        super().__init__(
            config, web_mode=True
        )  # Always run in headless mode for web UI
        self._last_frame = None

    def render(
        self, vehicle_state: VehicleState, target_position: carla.Location
    ) -> bool:
        """Override render to capture frames for web streaming"""
        # Call parent render method
        result = super().render(vehicle_state, target_position)

        # Capture frame for web streaming
        try:
            # Convert the surface to a numpy array
            frame = pygame.surfarray.array3d(self.display)
            # Convert from RGB to BGR for OpenCV
            frame = frame[:, :, ::-1]
            self._last_frame = frame
        except Exception as e:
            self.logger.error("Error capturing frame for web streaming", exc_info=e)

        return result

    def get_current_frame(self) -> Optional[np.ndarray]:
        """Get the current frame as a numpy array for web streaming"""
        return self._last_frame
