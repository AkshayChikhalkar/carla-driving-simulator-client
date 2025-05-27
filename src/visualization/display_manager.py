"""
Display management system using the facade pattern.
"""

import pygame
import numpy as np
import carla
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from ..core.sensors import SensorObserver, CameraData, SensorData
from ..utils.config import DisplayConfig
import time
import os
import sys
import logging
import math
from ..utils.logging import Logger

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
    
    def __init__(self, config: DisplayConfig, logger: Logger):
        """Initialize HUD with given font size"""
        self.logger = logger
        pygame.font.init()
        self.font = pygame.font.Font(pygame.font.get_default_font(), config.hud.font_size)
        self.alpha = config.hud.alpha
        self.colors = config.hud.colors
        
    def render(self, display, state):
        """Render HUD with current vehicle state"""
        try:
            # Create info strings
            scenario_str = f"Scenario: {state.scenario_name}"
            
            # Convert speed from m/s to km/h
            speed_kmh = state.speed * 3.6 if hasattr(state, 'speed') else 0.0
            speed_str = f"Speed: {speed_kmh:.1f} km/h"
            
            # Get control type
            control_type = "Keyboard" if state.controls.get('manual_gear_shift', False) else "Autopilot"
            control_str = f"Control: {control_type}"
            
            # Control state strings
            brake = state.controls.get('brake', 0.0)
            brake_str = f"Brake: {brake:.2f}"
            
            # Additional control info
            gear = state.controls.get('gear', 1)
            gear_str = f"Gear: {gear}"
            
            # Render text
            info_surface = pygame.Surface((300, 150))
            info_surface.set_alpha(self.alpha)
            info_surface.fill(pygame.Color(self.colors['background']))
            
            y_offset = 15
            line_spacing = 25
            for text in [scenario_str, speed_str, control_str, brake_str, gear_str]:
                text_surface = self.font.render(text, True, pygame.Color(self.colors['text']))
                info_surface.blit(text_surface, (15, y_offset))
                y_offset += line_spacing
            
            display.blit(info_surface, (10, 10))
        except Exception as e:
            self.logger.error("Error rendering HUD", exc_info=e)

class Minimap:
    """Minimap display showing vehicle and target positions"""
    
    def __init__(self, config: DisplayConfig, logger: Logger):
        """Initialize minimap"""
        self.logger = logger
        self.config = config
        self.width = 200
        self.height = 200
        self.margin = 20
        self.scale = 0.1  # Scale factor for converting world to minimap coordinates
        self.background = pygame.Color(config.hud.colors['background'])
        self.vehicle_color = pygame.Color(config.hud.colors['vehicle'])
        self.target_color = pygame.Color(config.hud.colors['target'])
        self.road_color = pygame.Color('gray')
        self.alpha = config.hud.alpha
    
    def render(self, surface: pygame.Surface, state: VehicleState, target_pos: carla.Location) -> None:
        """Render minimap with vehicle and target positions"""
        try:
            # Create minimap surface
            minimap = pygame.Surface((self.width, self.height))
            minimap.fill(self.background)
            minimap.set_alpha(self.alpha)
            
            # Get vehicle position
            vehicle_pos = state.position if hasattr(state, 'position') else (0, 0, 0)
            vehicle_heading = state.heading if hasattr(state, 'heading') else 0.0
            
            # Convert world coordinates to minimap coordinates
            vehicle_x = int(vehicle_pos[0] * self.scale + self.width / 2)
            vehicle_y = int(vehicle_pos[1] * self.scale + self.height / 2)
            target_x = int(target_pos.x * self.scale + self.width / 2)
            target_y = int(target_pos.y * self.scale + self.height / 2)
            
            # Draw vehicle (as triangle pointing in heading direction)
            vehicle_points = self._get_vehicle_triangle(vehicle_x, vehicle_y, vehicle_heading)
            pygame.draw.polygon(minimap, self.vehicle_color, vehicle_points)
            
            # Draw target (as cross)
            cross_size = 5
            pygame.draw.line(minimap, self.target_color,
                            (target_x - cross_size, target_y - cross_size),
                            (target_x + cross_size, target_y + cross_size), 2)
            pygame.draw.line(minimap, self.target_color,
                            (target_x - cross_size, target_y + cross_size),
                            (target_x + cross_size, target_y - cross_size), 2)
            
            # Blit minimap to main surface
            surface.blit(minimap, (surface.get_width() - self.width - 10,
                                  surface.get_height() - self.height - 10))
        except Exception as e:
            self.logger.error("Error rendering minimap", exc_info=e)

    def _get_vehicle_triangle(self, x: int, y: int, heading: float) -> list:
        """Get triangle points for vehicle representation"""
        size = 8
        angle = np.radians(heading)
        cos_a = np.cos(angle)
        sin_a = np.sin(angle)
        
        points = [
            (x + size * cos_a, y + size * sin_a),  # Front
            (x - size * cos_a + size/2 * sin_a, y - size * sin_a - size/2 * cos_a),  # Back right
            (x - size * cos_a - size/2 * sin_a, y - size * sin_a + size/2 * cos_a)   # Back left
        ]
        return [(int(px), int(py)) for px, py in points]

class CameraView(SensorObserver):
    """Camera view display"""
    def __init__(self, config: DisplayConfig, logger: Logger):
        """Initialize camera view"""
        self.logger = logger
        self.config = config
        self.surface: Optional[pygame.Surface] = None
        self.last_frame = None
    
    def on_sensor_data(self, data: SensorData) -> None:
        """Handle new camera data"""
        if isinstance(data, CameraData):
            try:
                # Convert numpy array to pygame surface
                array = data.image
                array = array[:, :, ::-1]  # Convert from RGB to BGR
                array = array.swapaxes(0, 1)  # Swap axes for pygame
                self.last_frame = array  # Store the last frame
                self.surface = pygame.surfarray.make_surface(array)
            except Exception as e:
                self.surface = None
    
    def render(self, display: pygame.Surface) -> None:
        """Render camera view to display"""
        try:
            if self.surface is not None:
                # Scale surface to match display size if needed
                display_size = display.get_size()
                if self.surface.get_size() != display_size:
                    try:
                        scaled_surface = pygame.transform.scale(self.surface, display_size)
                        display.blit(scaled_surface, (0, 0))
                    except Exception:
                        pass
                else:
                    display.blit(self.surface, (0, 0))
            elif self.last_frame is not None:
                # Try to recreate surface from last frame
                try:
                    self.surface = pygame.surfarray.make_surface(self.last_frame)
                    display.blit(self.surface, (0, 0))
                except Exception:
                    pass
            else:
                # If no camera data, fill with a dark gray color
                display.fill((32, 32, 32))
        except Exception:
            display.fill((32, 32, 32))  # Fallback to dark gray
            
    def cleanup(self) -> None:
        """Clean up camera view resources"""
        self.surface = None
        self.last_frame = None

def get_window_count():
    """Get count of existing CARLA Simulator windows"""
    try:
        import win32gui
        windows = []
        def enum_windows_callback(hwnd, windows):
            if "CARLA Simulator" in win32gui.GetWindowText(hwnd):
                windows.append(hwnd)
            return True
        win32gui.EnumWindows(enum_windows_callback, windows)
        return len(windows)
    except ImportError:
        return 0

class DisplayManager:
    """Facade for all visualization components"""
    
    def __init__(self, config: DisplayConfig, logger: Logger):
        """Initialize display manager"""
        self.logger = logger
        self.config = config
        
        # Initialize pygame display
        pygame.init()
        pygame.event.set_allowed([
            pygame.QUIT,
            pygame.KEYDOWN,
            pygame.KEYUP,
            pygame.WINDOWFOCUSLOST,
            pygame.WINDOWFOCUSGAINED,
            pygame.WINDOWMINIMIZED,
            pygame.WINDOWRESTORED,
            pygame.WINDOWEXPOSED,
            pygame.WINDOWRESIZED
        ])
        
        # Set up window position
        window_count = get_window_count()
        offset = window_count * 30
        os.environ['SDL_VIDEO_WINDOW_POS'] = f"{200 + offset},{200 + offset}"
        
        # Create resizable window with standard controls
        self.display = pygame.display.set_mode(
            (config.width, config.height),
            pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.RESIZABLE
        )
        pygame.display.set_caption(f"CARLA Simulator - Instance {window_count + 1}")
        
        # Initialize components
        self.hud = HUD(config, logger)
        self.minimap = Minimap(config, logger)
        self.camera_view = CameraView(config, logger)
        
        # Window state
        self.minimized = False
        self.focused = True
        self.should_quit = False
        self.current_size = (config.width, config.height)
        self.last_event_time = time.time()
        self.force_exit = False
        self.frame_count = 0
        
        # FPS tracking
        self.clock = pygame.time.Clock()
        self.fps_font = pygame.font.Font(None, 24)
        self.last_fps_update = time.time()
        self.current_fps = 0
    
    def handle_resize(self, size):
        """Handle window resize"""
        self.current_size = size
        self.display = pygame.display.set_mode(size, pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.RESIZABLE)
    
    def process_events(self):
        """Process pygame events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.should_quit = True
                return False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.should_quit = True
                    return False
            elif event.type == pygame.WINDOWRESIZED:
                self.handle_resize(event.size)
            elif event.type == pygame.WINDOWMINIMIZED:
                self.minimized = True
            elif event.type == pygame.WINDOWRESTORED:
                self.minimized = False
            elif event.type == pygame.WINDOWFOCUSLOST:
                self.focused = False
            elif event.type == pygame.WINDOWFOCUSGAINED:
                self.focused = True
        return True
    
    def render(self, vehicle_state: VehicleState, target_position: carla.Location) -> bool:
        """Render the display"""
        try:
            # Process events first
            if not self.process_events():
                return False
                
            # Skip rendering if minimized
            if self.minimized:
                return True
                
            # Update camera view first (as background)
            self._update_camera()
            
            # Update HUD
            self._update_hud(vehicle_state)
            
            # Update minimap
            self._update_minimap(vehicle_state, target_position)
            
            # Render FPS counter
            self._render_fps()
            
            # Update display
            pygame.display.flip()
            
            # Update frame count and clock
            self.frame_count += 1
            self.clock.tick(60)  # Cap at 60 FPS
            
            return True
        except Exception as e:
            self.logger.error("Error in display rendering", exc_info=e)
            return False

    def _render_fps(self):
        """Render FPS counter"""
        try:
            # Update FPS every second
            current_time = time.time()
            if current_time - self.last_fps_update >= 1.0:
                self.current_fps = self.clock.get_fps()
                self.last_fps_update = current_time
            
            # Render FPS text
            fps_text = f"FPS: {self.current_fps:.1f}"
            fps_surface = self.fps_font.render(fps_text, True, (255, 255, 255))
            
            # Create semi-transparent background
            bg_surface = pygame.Surface((100, 30))
            bg_surface.set_alpha(128)
            bg_surface.fill((0, 0, 0))
            
            # Blit background and text
            self.display.blit(bg_surface, (10, self.display.get_height() - 40))
            self.display.blit(fps_surface, (15, self.display.get_height() - 35))
            
        except Exception as e:
            self.logger.error("Error rendering FPS", exc_info=e)

    def _update_hud(self, vehicle_state: VehicleState) -> None:
        """Update HUD with vehicle state"""
        try:
            if not vehicle_state:
                return
                
            # Render HUD directly with vehicle state
            self.hud.render(self.display, vehicle_state)
            
        except Exception as e:
            self.logger.error("Error updating HUD", exc_info=e)
    
    def _update_minimap(self, vehicle_state: VehicleState, target_position: carla.Location) -> None:
        """Update minimap with vehicle and target positions"""
        try:
            if not vehicle_state or not target_position:
                return
                
            self.minimap.render(self.display, vehicle_state, target_position)
        except Exception as e:
            self.logger.error("Error updating minimap", exc_info=e)
    
    def _update_camera(self) -> None:
        """Update camera view"""
        try:
            self.camera_view.render(self.display)
        except Exception as e:
            self.logger.error("Error updating camera view", exc_info=e)

    def cleanup(self) -> None:
        """Clean up display resources"""
        try:
            if self.camera_view:
                self.camera_view.cleanup()
            pygame.quit()
        except Exception as e:
            self.logger.error("Error during cleanup", exc_info=e) 