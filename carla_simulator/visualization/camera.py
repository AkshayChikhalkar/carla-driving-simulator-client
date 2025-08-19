"""
Camera visualization module for the CARLA Driving Simulator.
Handles camera setup, image processing, and display.
"""

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import carla
import pygame
import numpy as np
from typing import Optional, Tuple, Dict, Any
import weakref


class CameraManager:
    """Manages camera setup and visualization."""

    def __init__(self, parent_actor: carla.Actor, config: Dict[str, Any]):
        """
        Initialize camera manager.

        Args:
            parent_actor: Actor to attach camera to
            config: Camera configuration dictionary
        """
        self.sensor = None
        self._parent = parent_actor
        self.config = config
        self.surface = None
        self._setup_camera()

    def _setup_camera(self):
        """Set up the camera sensor."""
        world = self._parent.get_world()
        blueprint = world.get_blueprint_library().find("sensor.camera.rgb")
        blueprint.set_attribute("image_size_x", str(self.config["display_width"]))
        blueprint.set_attribute("image_size_y", str(self.config["display_height"]))

        transform = carla.Transform(carla.Location(x=1.6, z=1.7))
        self.sensor = world.spawn_actor(blueprint, transform, attach_to=self._parent)
        weak_self = weakref.ref(self)
        self.sensor.listen(lambda image: self._process_image(weak_self, image))

    @staticmethod
    def _process_image(weak_self, image):
        """
        Process camera image.

        Args:
            weak_self: Weak reference to self
            image: Camera image data
        """
        self = weak_self()
        if not self:
            return

        if not self.surface:
            w, h = self.config["display_width"], self.config["display_height"]
            self.surface = pygame.Surface((w, h), pygame.HWSURFACE | pygame.DOUBLEBUF)
            self.surface.set_alpha(None)

        array = np.frombuffer(image.raw_data, dtype=np.dtype("uint8"))
        array = np.reshape(array, (image.height, image.width, 4))
        array = array[:, :, :3]
        array = array[:, :, ::-1]
        surface = pygame.surfarray.make_surface(array.swapaxes(0, 1))
        self.surface.blit(surface, (0, 0))

    def get_surface(self) -> Optional[pygame.Surface]:
        """
        Get the current camera surface.

        Returns:
            Pygame surface containing the camera image
        """
        return self.surface

    def destroy(self):
        """Destroy the camera sensor."""
        if self.sensor is not None:
            self.sensor.destroy()
            self.sensor = None
        if self.surface is not None:
            self.surface = None


class DisplayManager:
    """Manages the display window and HUD elements."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize display manager.

        Args:
            config: Display configuration dictionary
        """
        self.config = config
        self.width = config["display_width"]
        self.height = config["display_height"]
        self._setup_display()

    def _setup_display(self):
        """Set up the display window."""
        pygame.init()
        pygame.font.init()
        self.display = pygame.display.set_mode(
            (self.width, self.height), pygame.HWSURFACE | pygame.DOUBLEBUF
        )
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(pygame.font.get_default_font(), 20)

    def render(
        self, camera_surface: Optional[pygame.Surface], vehicle_state: Dict[str, Any]
    ):
        """
        Render the display with camera feed and HUD.

        Args:
            camera_surface: Surface containing camera image
            vehicle_state: Current vehicle state information
        """
        if camera_surface is not None:
            self.display.blit(camera_surface, (0, 0))

        self._render_hud(vehicle_state)
        pygame.display.flip()
        self.clock.tick_busy_loop(60)

    def _render_hud(self, vehicle_state: Dict[str, Any]):
        """
        Render HUD elements.

        Args:
            vehicle_state: Current vehicle state information
        """
        # Speed
        speed_text = f"Speed: {vehicle_state.get('speed', 0):.1f} km/h"
        speed_surface = self.font.render(speed_text, True, (255, 255, 255))
        self.display.blit(speed_surface, (10, 10))

        # Location
        location = vehicle_state.get("location", (0, 0, 0))
        location_text = (
            f"Location: ({location[0]:.1f}, {location[1]:.1f}, {location[2]:.1f})"
        )
        location_surface = self.font.render(location_text, True, (255, 255, 255))
        self.display.blit(location_surface, (10, 40))

        # Control
        control = vehicle_state.get("control", {})
        control_text = f"Throttle: {control.get('throttle', 0):.1f} | "
        control_text += f"Steer: {control.get('steer', 0):.1f} | "
        control_text += f"Brake: {control.get('brake', 0):.1f}"
        control_surface = self.font.render(control_text, True, (255, 255, 255))
        self.display.blit(control_surface, (10, 70))

    def destroy(self):
        """Clean up display resources."""
        pygame.quit()
