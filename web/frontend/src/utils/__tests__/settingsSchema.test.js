import { validateSettings, getDefaultSettings, mergeSettings } from '../settingsValidation';

describe('settingsSchema Utility', () => {
  const validSettings = {
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
      minimap_enabled: true,
      hud: {
        font_size: 18,
        font_name: 'Arial',
        alpha: 255,
        colors: {
          target: 'green',
          vehicle: 'blue',
          text: 'white',
          background: 'black'
        }
      },
      minimap: {
        width: 200,
        height: 150,
        position: 'top_right',
        zoom: 1.0
      }
    }
  };

  test('validates valid settings', () => {
    const result = validateSettings(validSettings);
    expect(result.isValid).toBe(true);
    expect(result.errors).toEqual([]);
  });

  test('validates server settings', () => {
    const settings = {
      ...validSettings,
      server: {
        ...validSettings.server,
        port: -1
      }
    };

    const result = validateSettings(settings);
    expect(result.isValid).toBe(false);
    expect(result.errors).toContain('Server port must be between 1 and 65535');
  });

  test('validates world settings', () => {
    const settings = {
      ...validSettings,
      world: {
        ...validSettings.world,
        fixed_delta_seconds: -0.1
      }
    };

    const result = validateSettings(settings);
    expect(result.isValid).toBe(false);
    expect(result.errors).toContain('Fixed delta seconds must be positive');
  });

  test('validates simulation settings', () => {
    const settings = {
      ...validSettings,
      simulation: {
        ...validSettings.simulation,
        max_speed: -10
      }
    };

    const result = validateSettings(settings);
    expect(result.isValid).toBe(false);
    expect(result.errors).toContain('Maximum speed must be positive');
  });

  test('validates display settings', () => {
    const settings = {
      ...validSettings,
      display: {
        ...validSettings.display,
        width: 0
      }
    };

    const result = validateSettings(settings);
    expect(result.isValid).toBe(false);
    expect(result.errors).toContain('Display width must be positive');
  });

  test('validates weather settings', () => {
    const settings = {
      ...validSettings,
      world: {
        ...validSettings.world,
        weather: {
          ...validSettings.world.weather,
          cloudiness: 101
        }
      }
    };

    const result = validateSettings(settings);
    expect(result.isValid).toBe(false);
    expect(result.errors).toContain('Cloudiness must be between 0 and 100');
  });

  test('validates physics settings', () => {
    const settings = {
      ...validSettings,
      world: {
        ...validSettings.world,
        physics: {
          ...validSettings.world.physics,
          max_substeps: 0
        }
      }
    };

    const result = validateSettings(settings);
    expect(result.isValid).toBe(false);
    expect(result.errors).toContain('Maximum substeps must be positive');
  });

  test('validates traffic settings', () => {
    const settings = {
      ...validSettings,
      world: {
        ...validSettings.world,
        traffic: {
          ...validSettings.world.traffic,
          ignore_lights_percentage: 101
        }
      }
    };

    const result = validateSettings(settings);
    expect(result.isValid).toBe(false);
    expect(result.errors).toContain('Ignore lights percentage must be between 0 and 100');
  });

  test('provides default settings', () => {
    const defaults = getDefaultSettings();
    const result = validateSettings(defaults);
    expect(result.isValid).toBe(true);
  });

  test('merges settings with defaults', () => {
    const partialSettings = {
      server: {
        host: 'carla.local'
      }
    };

    const merged = mergeSettings(partialSettings);
    expect(merged.server.host).toBe('carla.local');
    expect(merged.server.port).toBe(2000); // Default value
  });

  test('validates required fields', () => {
    const settings = { ...validSettings };
    delete settings.server;

    const result = validateSettings(settings);
    expect(result.isValid).toBe(false);
    expect(result.errors).toContain('Server settings are required');
  });

  test('validates nested required fields', () => {
    const settings = {
      ...validSettings,
      server: {
        port: 2000
      }
    };

    const result = validateSettings(settings);
    expect(result.isValid).toBe(false);
    expect(result.errors).toContain('Server host is required');
  });

  test('validates field types', () => {
    const settings = {
      ...validSettings,
      server: {
        ...validSettings.server,
        port: '2000' // Should be number
      }
    };

    const result = validateSettings(settings);
    expect(result.isValid).toBe(false);
    expect(result.errors).toContain('Server port must be a number');
  });

  test('validates enum values', () => {
    const settings = {
      ...validSettings,
      logging: {
        ...validSettings.logging,
        log_level: 'INVALID'
      }
    };

    const result = validateSettings(settings);
    expect(result.isValid).toBe(false);
    expect(result.errors).toContain('Invalid log level');
  });
});
