"""
Display management system using the facade pattern.
"""

import os
# Ensure headless-friendly SDL defaults even if backend didn't set them yet
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import numpy as np
import carla
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from ..core.sensors import SensorObserver, CameraData, SensorData
from ..utils.config import DisplayConfig
from ..utils.default_config import DISPLAY_CONFIG
from ..utils.logging import Logger
import time
import os
import sys
import logging
import math


@dataclass
class VehicleState:
    """Vehicle state information for display"""

    speed: float
    position: Tuple[float, float, float]
    heading: float
    distance_to_target: float
    controls: Dict[str, float]
    speed_kmh: float
    scenario_name: str = "No Scenario"  # Default value if no scenario is running


class HUD:
    """Heads Up Display showing vehicle telemetry"""

    def __init__(self, config: DisplayConfig):
        """Initialize HUD with given font size"""
        pygame.font.init()
        self.font = pygame.font.Font(
            pygame.font.get_default_font(), config.hud.font_size
        )
        self.text_color = pygame.Color(config.hud.colors["text"])
        self.bg_color = pygame.Color(config.hud.colors["background"])
        self.alpha = config.hud.alpha

    def render(self, display, state):
        """Render HUD with current vehicle state"""
        try:
            # Create info strings
            scenario_str = f"Scenario: {state.scenario_name}"

            # Convert speed from m/s to km/h
            speed_kmh = state.speed * 3.6 if hasattr(state, "speed") else 0.0
            speed_str = f"Speed: {speed_kmh:.1f} km/h"

            # Get control type
            control_type = (
                "Keyboard"
                if state.controls.get("manual_gear_shift", False)
                else "Autopilot"
            )
            control_str = f"Control: {control_type}"

            # Control state strings
            brake = state.controls.get("brake", 0.0)
            brake_str = f"Brake: {brake:.2f}"

            # Additional control info
            gear = state.controls.get("gear", 1)
            gear_str = f"Gear: {gear}"

            # Create semi-transparent background surface
            bg_surface = pygame.Surface((250, 120))
            bg_surface.set_alpha(self.alpha)  # Use alpha from config
            bg_surface.fill(self.bg_color)

            # Blit the semi-transparent background
            display.blit(bg_surface, (10, 10))

            # Render text directly to display
            y_offset = 15
            line_spacing = 25
            for text in [scenario_str, speed_str, control_str, brake_str, gear_str]:
                text_surface = self.font.render(text, True, self.text_color)
                display.blit(text_surface, (15, y_offset))
                y_offset += line_spacing

        except Exception as e:
            logging.error("Error rendering HUD", exc_info=e)


class Minimap:
    """Minimap display showing vehicle and target positions"""

    def __init__(self, config: DisplayConfig):
        """Initialize minimap"""
        self.config = config
        self.width = 200
        self.height = 200
        self.margin = 20
        self.scale = 0.1  # Scale factor for converting world to minimap coordinates
        self.background = pygame.Color(config.hud.colors["background"])
        self.vehicle_color = pygame.Color(config.hud.colors["vehicle"])
        self.target_color = pygame.Color(config.hud.colors["target"])
        self.road_color = pygame.Color("gray")
        self.alpha = config.hud.alpha

    def render(
        self, surface: pygame.Surface, state: VehicleState, target_pos: carla.Location
    ) -> None:
        """Render minimap with vehicle and target positions"""
        try:
            # Create minimap surface
            minimap = pygame.Surface((self.width, self.height))
            minimap.fill(self.background)
            minimap.set_alpha(self.alpha)

            # Get vehicle position
            vehicle_pos = state.position if hasattr(state, "position") else (0, 0, 0)
            vehicle_heading = state.heading if hasattr(state, "heading") else 0.0

            # Convert world coordinates to minimap coordinates
            vehicle_x = int(vehicle_pos[0] * self.scale + self.width / 2)
            vehicle_y = int(vehicle_pos[1] * self.scale + self.height / 2)
            target_x = int(target_pos.x * self.scale + self.width / 2)
            target_y = int(target_pos.y * self.scale + self.height / 2)

            # Draw vehicle (as triangle pointing in heading direction)
            vehicle_points = self._get_vehicle_triangle(
                vehicle_x, vehicle_y, vehicle_heading
            )
            pygame.draw.polygon(minimap, self.vehicle_color, vehicle_points)

            # Draw target (as cross)
            cross_size = 5
            pygame.draw.line(
                minimap,
                self.target_color,
                (target_x - cross_size, target_y - cross_size),
                (target_x + cross_size, target_y + cross_size),
                2,
            )
            pygame.draw.line(
                minimap,
                self.target_color,
                (target_x - cross_size, target_y + cross_size),
                (target_x + cross_size, target_y - cross_size),
                2,
            )

            # Blit minimap to main surface
            surface.blit(
                minimap,
                (
                    surface.get_width() - self.width - 10,
                    surface.get_height() - self.height - 10,
                ),
            )
        except Exception as e:
            logging.error("Error rendering minimap", exc_info=e)

    def _get_vehicle_triangle(self, x: int, y: int, heading: float) -> list:
        """Get triangle points for vehicle representation"""
        size = 8
        angle = np.radians(heading)
        cos_a = np.cos(angle)
        sin_a = np.sin(angle)

        points = [
            (x + size * cos_a, y + size * sin_a),  # Front
            (
                x - size * cos_a + size / 2 * sin_a,
                y - size * sin_a - size / 2 * cos_a,
            ),  # Back right
            (
                x - size * cos_a - size / 2 * sin_a,
                y - size * sin_a + size / 2 * cos_a,
            ),  # Back left
        ]
        return [(int(px), int(py)) for px, py in points]


class CameraView(SensorObserver):
    """Camera view display"""

    def __init__(self, config: DisplayConfig):
        """Initialize camera view"""
        self.config = config
        self.surface: Optional[pygame.Surface] = None
        self.last_frame = None
        self.logger = Logger()

    def on_sensor_data(self, data: SensorData) -> None:
        """Handle new camera data"""
        if isinstance(data, CameraData):
            try:
                # Convert numpy array to pygame surface
                array = data.image
                if array is None:
                    self.logger.warning("Received empty camera data")
                    return


                # Convert from RGB to BGR if needed
                if array.shape[2] == 3:  # Ensure it's a color image
                    array = array[:, :, ::-1]  # Convert from RGB to BGR

                # Swap axes for pygame
                array = array.swapaxes(0, 1)

                # Store the last frame
                self.last_frame = array

                # Create surface
                self.surface = pygame.surfarray.make_surface(array)

                if self.surface is None:
                    self.logger.warning("Failed to create surface from camera data")

            except Exception as e:
                self.logger.error("Error processing camera data", exc_info=e)
                self.surface = None

    def render(self, display: pygame.Surface) -> None:
        """Render camera view to display"""
        try:
            if self.surface is not None:
                # Scale surface to match display size if needed
                display_size = display.get_size()
                if self.surface.get_size() != display_size:
                    try:
                        scaled_surface = pygame.transform.scale(
                            self.surface, display_size
                        )
                        display.blit(scaled_surface, (0, 0))
                    except Exception as e:
                        self.logger.error("Error scaling camera surface", exc_info=e)
                        display.fill((32, 32, 32))
                else:
                    display.blit(self.surface, (0, 0))
            elif self.last_frame is not None:
                # Try to recreate surface from last frame
                try:
                    self.surface = pygame.surfarray.make_surface(self.last_frame)
                    display.blit(self.surface, (0, 0))
                except Exception as e:
                    self.logger.error(
                        "Error recreating surface from last frame", exc_info=e
                    )
                    display.fill((32, 32, 32))
            else:
                # If no camera data, fill with a dark gray color
                display.fill((32, 32, 32))
        except Exception as e:
            self.logger.error("Error rendering camera view", exc_info=e)
            display.fill((32, 32, 32))  # Fallback to dark gray

    def cleanup(self) -> None:
        """Clean up camera view resources"""
        self.surface = None
        self.last_frame = None


# def get_window_count():
#     """Get count of existing CARLA Simulator windows"""
#     try:
#         import win32gui
#         windows = []
#         def enum_windows_callback(hwnd, windows):
#             if "CARLA Simulator" in win32gui.GetWindowText(hwnd):
#                 windows.append(hwnd)
#             return True
#         win32gui.EnumWindows(enum_windows_callback, windows)
#         return len(windows)
#     except ImportError:
#         return 0


class DisplayManager:
    """Facade for all visualization components"""

    def __init__(self, config: DisplayConfig, web_mode: bool = False):
        """Initialize display manager

        Args:
            config: Display configuration
            web_mode: If True, run in web mode (headless)
        """
        self.config = config
        self.web_mode = web_mode
        self.screen = None
        self.clock = None
        self.font = None
        self.minimized = False
        self.camera_view = None
        self.current_frame = None
        self.frame_buffer = None
        self.closed = False

        # Initialize pygame conditionally for web/CLI
        if web_mode:
            # Lightweight init for headless mode; avoid creating full window/font stacks
            try:
                pygame.init()
            except Exception:
                pass
            self.screen = None
            self.clock = None
            self.font = None
        else:
            pygame.init()
            # Create a window for CLI mode
            pygame.display.set_caption("CARLA Driving Simulator")
            self.screen = pygame.display.set_mode(
                (config.width, config.height),
                pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.RESIZABLE,
            )
            self.clock = pygame.time.Clock()
            self.font = pygame.font.Font(None, 24)

        # Initialize components with config
        self.hud = HUD(config)
        self.minimap = Minimap(config)
        self.camera_view = CameraView(config)

        # Store the last rendered frame
        self.last_frame = None

        # Set up logging
        self.logger = logging.getLogger(__name__)

        # FPS tracking
        self.last_fps_update = time.time()
        self.current_fps = 0

    def handle_resize(self, size):
        """Handle window resize"""
        if not self.web_mode:
            self.screen = pygame.display.set_mode(
                size, pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.RESIZABLE
            )

    def process_events(self):
        """Process pygame events"""
        if self.web_mode:
            return True

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
            elif event.type == pygame.WINDOWRESIZED:
                self.handle_resize(event.size)
            elif event.type == pygame.WINDOWMINIMIZED:
                self.minimized = True
            elif event.type == pygame.WINDOWRESTORED:
                self.minimized = False
        return True

    def render(
        self, vehicle_state: VehicleState, target_position: carla.Location
    ) -> bool:
        """Render the display"""
        try:
            # If pygame was quit during cleanup or not initialized, skip rendering
            if self.closed or not pygame.get_init() or not pygame.font.get_init():
                return False
            # Process events first if not in web mode
            if not self.web_mode and not self.process_events():
                return False

            # Skip rendering if minimized and not in web mode
            if not self.web_mode and self.minimized:
                return True

            # Clear the screen first
            if self.web_mode:
                frame = np.zeros((self.config.height, self.config.width, 3), dtype=np.uint8)
            else:
                self.screen.fill((0, 0, 0))

            # Update camera view first (as background)
            if self.web_mode:
                if self.camera_view and getattr(self.camera_view, 'last_frame', None) is not None:
                    cam = self.camera_view.last_frame
                    try:
                        # cam is stored as (width, height, 3) in RGB for pygame rendering.
                        # For web streaming we need (height, width, 3) BGR for OpenCV encoding.
                        frame_rgb_hwc = cam.swapaxes(0, 1)
                        frame = frame_rgb_hwc[:, :, ::-1]  # RGB -> BGR
                        if frame.shape[0] != self.config.height or frame.shape[1] != self.config.width:
                            try:
                                import cv2
                                frame = cv2.resize(frame, (self.config.width, self.config.height))
                            except Exception:
                                pass
                    except Exception:
                        frame = np.zeros((self.config.height, self.config.width, 3), dtype=np.uint8)
                else:
                    frame = np.zeros((self.config.height, self.config.width, 3), dtype=np.uint8)
            else:
                self._update_camera()

            # Update HUD
            if not self.web_mode:
                self._update_hud(vehicle_state)

            # Update minimap
            if not self.web_mode:
                self._update_minimap(vehicle_state, target_position)

            # Update FPS counter for both CLI and web UI modes
            current_time = time.time()
            if not hasattr(self, "_last_fps_update"):
                self._last_fps_update = current_time
                self._frame_count = 0
                self._current_fps = 0

            self._frame_count += 1

            # Update FPS every second
            if current_time - self._last_fps_update >= 1.0:
                self._current_fps = self._frame_count / (
                    current_time - self._last_fps_update
                )
                self._frame_count = 0
                self._last_fps_update = current_time

            # Render FPS counter
            if not self.web_mode:
                # Guard font rendering
                try:
                    fps_text = self.font.render(
                        f"FPS: {self._current_fps:.1f}", True, (255, 255, 255)
                    )
                except Exception:
                    return False
                # Position FPS text at bottom left with 10px padding
                fps_rect = fps_text.get_rect()
                fps_rect.bottomleft = (10, self.screen.get_height() - 10)
                self.screen.blit(fps_text, fps_rect)

            # Update the display and tick clock if not in web mode
            if not self.web_mode:
                pygame.display.flip()
                self.clock.tick(self.config.fps)

            # Store frame for web UI
            try:
                if self.web_mode:
                    # Store BGR(HxW) for the websocket encoder
                    self.last_frame = frame
                else:
                    frame_np = pygame.surfarray.array3d(self.screen)
                    frame_np = frame_np.swapaxes(0, 1)
                    self.last_frame = frame_np
                if self.web_mode and self._frame_count % 30 == 0:
                    self.logger.debug(f"Web mode: Captured frame with shape {self.last_frame.shape}")
            except Exception as e:
                self.logger.error(f"Error capturing frame for web UI: {str(e)}")
                if self.web_mode:
                    fallback_frame = np.zeros((self.config.height, self.config.width, 3), dtype=np.uint8)
                    fallback_frame.fill(32)
                    self.last_frame = fallback_frame

            return True
        except Exception as e:
            self.logger.error("Error in display rendering", exc_info=e)
            return False

    def _update_hud(self, vehicle_state: VehicleState) -> None:
        """Update HUD with vehicle state"""
        try:
            if not vehicle_state:
                return
            self.hud.render(self.screen, vehicle_state)
        except Exception as e:
            self.logger.error("Error updating HUD", exc_info=e)

    def _update_minimap(
        self, vehicle_state: VehicleState, target_position: carla.Location
    ) -> None:
        """Update minimap with vehicle and target positions"""
        try:
            if not vehicle_state or not target_position:
                return
            self.minimap.render(self.screen, vehicle_state, target_position)
        except Exception as e:
            self.logger.error("Error updating minimap", exc_info=e)

    def _update_camera(self) -> None:
        """Update camera view"""
        try:
            if self.camera_view:
                self.camera_view.render(self.screen)
            else:
                # Fill with a dark gray color if no camera view
                self.screen.fill((32, 32, 32))
        except Exception as e:
            self.logger.error("Error updating camera view", exc_info=e)
            # Fill with a dark gray color on error
            self.screen.fill((32, 32, 32))

    def get_current_frame(self) -> Optional[np.ndarray]:
        """Get the current frame as a numpy array"""
        return self.last_frame

    def cleanup(self) -> None:
        """Clean up display resources"""
        try:
            self.closed = True
            if self.camera_view:
                self.camera_view.cleanup()
            # In web/headless mode we keep SDL around for the process to avoid
            # race conditions where other threads still reference pygame
            if not self.web_mode:
                pygame.quit()
        except Exception as e:
            self.logger.error("Error during cleanup", exc_info=e)
