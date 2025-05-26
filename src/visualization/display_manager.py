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
    
    def __init__(self, font_size=20):
        """Initialize HUD with given font size"""
        pygame.font.init()
        self.font = pygame.font.Font(pygame.font.get_default_font(), font_size)
        
    def render(self, display, state):
        """Render HUD with current vehicle state"""
        # Create info strings
        scenario_str = f"Scenario: {state.scenario_name}"
        speed_str = f"Speed: {state.speed_kmh:.1f} km/h"  # Using speed_kmh property
        control_type = "Keyboard" if state.controls.get('manual_gear_shift', False) else "Autopilot"
        control_str = f"Control: {control_type}"
        #heading_str = f"Heading: {state.heading:.1f}°"
        #distance_str = f"Distance to target: {state.distance_to_target:.1f}m"
        
        # Control state strings
        brake_str = f"Brake: {state.controls.get('brake', 0.0):.2f}"
        #steer_str = f"Steer: {state.controls.get('steer', 0.0):.2f}"
        
        # Additional control info
        gear_str = f"Gear: {state.controls.get('gear', 1)}"
        
        # Render text
        info_surface = pygame.Surface((300, 200))
        info_surface.set_alpha(128)
        info_surface.fill((0, 0, 0))
        
        y_offset = 10
        for text in [scenario_str, speed_str, control_str, #heading_str, #distance_str, 
                    brake_str, #steer_str, 
                    gear_str]:
            text_surface = self.font.render(text, True, (255, 255, 255))
            info_surface.blit(text_surface, (10, y_offset))
            y_offset += 20
        
        display.blit(info_surface, (10, 10))

class Minimap:
    """Minimap display showing vehicle and target positions"""
    
    def __init__(self, config: DisplayConfig):
        """Initialize minimap"""
        self.config = config
        self.width = 200
        self.height = 200
        self.margin = 20
        self.scale = 0.1  # Scale factor for converting world to minimap coordinates
        self.background = pygame.Color('black')
        self.vehicle_color = pygame.Color('green')
        self.target_color = pygame.Color('red')
        self.road_color = pygame.Color('gray')
        self.alpha = 128
    
    def render(self, surface: pygame.Surface, state: VehicleState, target_pos: carla.Location) -> None:
        """Render minimap with vehicle and target positions"""
        # Create minimap surface
        minimap = pygame.Surface((self.width, self.height))
        minimap.fill(self.background)
        minimap.set_alpha(self.alpha)
        
        # Convert world coordinates to minimap coordinates
        vehicle_x = int(state.position[0] * self.scale + self.width / 2)
        vehicle_y = int(state.position[1] * self.scale + self.height / 2)
        target_x = int(target_pos.x * self.scale + self.width / 2)
        target_y = int(target_pos.y * self.scale + self.height / 2)
        
        # Draw vehicle (as triangle pointing in heading direction)
        vehicle_points = self._get_vehicle_triangle(vehicle_x, vehicle_y, state.heading)
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
    def __init__(self, config: DisplayConfig):
        """Initialize camera view"""
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
    
    def __init__(self, config: DisplayConfig):
        """Initialize display manager"""
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
            pygame.WINDOWEXPOSED
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
        self.hud = HUD()
        self.minimap = Minimap(config)
        self.camera_view = CameraView(config)
        
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
    
    def render(self, state: VehicleState, target_pos: carla.Location) -> bool:
        """Render the current frame"""
        try:
            # Process events first
            if not self.process_events():
                return False

            # Skip rendering if minimized
            if self.minimized:
                return True

            # Clear display
            self.display.fill((0, 0, 0))

            # Render camera view
            self.camera_view.render(self.display)

            # Render HUD
            self.hud.render(self.display, state)

            # Render minimap
            self.minimap.render(self.display, state, target_pos)
            
            # Update FPS counter
            current_time = time.time()
            if current_time - self.last_fps_update >= 0.5:  # Update FPS every 0.5 seconds
                self.current_fps = self.clock.get_fps()
                self.last_fps_update = current_time
            
            # Render FPS in top-right corner
            fps_text = self.fps_font.render(f"FPS: {self.current_fps:.1f}", True, (255, 255, 255))
            self.display.blit(fps_text, (self.current_size[0] - 120, 10))

            # Update display
            pygame.display.flip()
            self.frame_count += 1
            
            # Control frame rate
            self.clock.tick(60)

            return True

        except Exception as e:
            print(f"Error in display rendering: {e}")
            return False
    
    def cleanup(self) -> None:
        """Clean up resources"""
        try:
            pygame.quit()
        except Exception as e:
            print(f"Error during cleanup: {e}") 