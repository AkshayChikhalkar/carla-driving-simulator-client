import { getValue } from './settingsSchema';

export const DEFAULT_SETTINGS = {
  server: {
    host: 'localhost',
    port: 2000,
    timeout: 5.0
  },
  world: {
    map: 'Town01',
    fixed_delta_seconds: 0.05,
    target_distance: 10.0,
    num_vehicles: 0,
    enable_collision: true,
    synchronous_mode: true,
    weather: {
      cloudiness: 10.0,
      precipitation: 0.0,
      wind_intensity: 0.0
    },
    physics: {
      max_substep_delta_time: 0.01,
      max_substeps: 10
    },
    traffic: {
      distance_to_leading_vehicle: 5.0,
      speed_difference_percentage: 20.0,
      ignore_lights_percentage: 0.0,
      ignore_signs_percentage: 0.0
    }
  },
  simulation: {
    timeout: 20.0,
    max_speed: 50.0,
    simulation_time: 300,
    update_rate: 60.0,
    speed_change_threshold: 0.1,
    position_change_threshold: 0.1,
    heading_change_threshold: 0.1,
    target_tolerance: 1.0,
    max_collision_force: 1000.0
  },
  logging: {
    log_level: 'INFO',
    enabled: true,
    directory: 'logs'
  },
  display: {
    width: 800,
    height: 600,
    fps: 60,
    hud_enabled: true,
    minimap_enabled: true
  }
};

export function validateSettings(settings) {
  const errors = [];

  // Validate required sections
  if (!settings.server) errors.push('Server settings are required');
  if (!settings.world) errors.push('World settings are required');
  if (!settings.simulation) errors.push('Simulation settings are required');

  // Validate server settings
  if (settings.server) {
    if (!settings.server.host) errors.push('Server host is required');
    if (typeof settings.server.port !== 'number') errors.push('Server port must be a number');
    if (settings.server.port < 1 || settings.server.port > 65535) errors.push('Server port must be between 1 and 65535');
  }

  // Validate world settings
  if (settings.world) {
    if (settings.world.fixed_delta_seconds <= 0) errors.push('Fixed delta seconds must be positive');
    if (settings.world.weather?.cloudiness < 0 || settings.world.weather?.cloudiness > 100) errors.push('Cloudiness must be between 0 and 100');
    if (settings.world.physics?.max_substeps <= 0) errors.push('Maximum substeps must be positive');
    if (settings.world.traffic?.ignore_lights_percentage < 0 || settings.world.traffic?.ignore_lights_percentage > 100) errors.push('Ignore lights percentage must be between 0 and 100');
  }

  // Validate simulation settings
  if (settings.simulation) {
    if (settings.simulation.max_speed <= 0) errors.push('Maximum speed must be positive');
  }

  // Validate display settings
  if (settings.display) {
    if (settings.display.width <= 0) errors.push('Display width must be positive');
    if (settings.display.height <= 0) errors.push('Display height must be positive');
  }

  // Validate logging settings
  if (settings.logging) {
    const validLogLevels = ['DEBUG', 'INFO', 'WARNING', 'ERROR'];
    if (!validLogLevels.includes(settings.logging.log_level)) errors.push('Invalid log level');
  }

  return {
    isValid: errors.length === 0,
    errors
  };
}

export function getDefaultSettings() {
  return DEFAULT_SETTINGS;
}

export function mergeSettings(partialSettings) {
  return {
    ...DEFAULT_SETTINGS,
    ...partialSettings,
    server: {
      ...DEFAULT_SETTINGS.server,
      ...partialSettings.server
    },
    world: {
      ...DEFAULT_SETTINGS.world,
      ...partialSettings.world
    },
    simulation: {
      ...DEFAULT_SETTINGS.simulation,
      ...partialSettings.simulation
    },
    logging: {
      ...DEFAULT_SETTINGS.logging,
      ...partialSettings.logging
    },
    display: {
      ...DEFAULT_SETTINGS.display,
      ...partialSettings.display
    }
  };
}
