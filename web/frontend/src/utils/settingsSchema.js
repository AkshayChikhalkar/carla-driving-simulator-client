// Declarative schema for settings fields, VS Code–style categories

export const SETTINGS_CATEGORIES = [
  {
    key: 'server',
    label: 'Server',
    fields: [
      { path: 'server.host', label: 'Host', type: 'string' },
      { path: 'server.port', label: 'Port', type: 'number', min: 1, max: 65535 },
      { path: 'server.timeout', label: 'Timeout (s)', type: 'number', min: 1, step: 0.1 },
      { path: 'server.connection.max_retries', label: 'Max Retries', type: 'number', min: 0 },
      { path: 'server.connection.retry_delay', label: 'Retry Delay (s)', type: 'number', min: 0, step: 0.1 },
    ],
  },
  {
    key: 'simulation',
    label: 'Simulation',
    fields: [
      { path: 'simulation.max_speed', label: 'Max Speed (km/h)', type: 'number' },
      { path: 'simulation.simulation_time', label: 'Simulation Time (s)', type: 'number' },
      { path: 'simulation.update_rate', label: 'Update Rate (Hz)', type: 'number', step: 0.1 },
      { path: 'simulation.speed_change_threshold', label: 'Speed Change Threshold (m/s)', type: 'number', step: 0.1 },
      { path: 'simulation.position_change_threshold', label: 'Position Change Threshold (m)', type: 'number', step: 0.1 },
      { path: 'simulation.heading_change_threshold', label: 'Heading Change Threshold (deg)', type: 'number', step: 0.1 },
      { path: 'simulation.target_tolerance', label: 'Target Tolerance (m)', type: 'number', step: 0.1 },
      { path: 'simulation.max_collision_force', label: 'Max Collision Force (N)', type: 'number' },
    ],
  },
  {
    key: 'world',
    label: 'World',
    fields: [
      { path: 'world.map', label: 'Map', type: 'string' },
      { path: 'world.fixed_delta_seconds', label: 'Fixed Delta (s)', type: 'number', step: 0.0001 },
      { path: 'world.target_distance', label: 'Target Distance (m)', type: 'number' },
      { path: 'world.num_vehicles', label: 'Number of Vehicles', type: 'number', min: 0 },
      { path: 'world.enable_collision', label: 'Enable Collision', type: 'boolean' },
      { path: 'world.synchronous_mode', label: 'Synchronous Mode', type: 'boolean' },
      { path: 'world.weather.cloudiness', label: 'Cloudiness (%)', type: 'number', min: 0, max: 100 },
      { path: 'world.weather.precipitation', label: 'Precipitation (%)', type: 'number', min: 0, max: 100 },
      { path: 'world.physics.max_substep_delta_time', label: 'Max Substep Delta (s)', type: 'number', step: 0.0001 },
      { path: 'world.physics.max_substeps', label: 'Max Substeps', type: 'number', min: 0 },
      { path: 'world.traffic.distance_to_leading_vehicle', label: 'Distance to Leading (m)', type: 'number', step: 0.1 },
      { path: 'world.traffic.speed_difference_percentage', label: 'Speed Difference (%)', type: 'number', step: 1 },
    ],
  },
  {
    key: 'sensors',
    label: 'Sensors',
    fields: [
      { path: 'sensors.camera.enabled', label: 'Camera Enabled', type: 'boolean' },
      { path: 'sensors.camera.width', label: 'Camera Width', type: 'number' },
      { path: 'sensors.camera.height', label: 'Camera Height', type: 'number' },
      { path: 'sensors.camera.fov', label: 'Camera FOV', type: 'number' },
      { path: 'sensors.camera.x', label: 'Camera X', type: 'number', step: 0.1 },
      { path: 'sensors.camera.y', label: 'Camera Y', type: 'number', step: 0.1 },
      { path: 'sensors.camera.z', label: 'Camera Z', type: 'number', step: 0.1 },
      { path: 'sensors.collision.enabled', label: 'Collision Enabled', type: 'boolean' },
      { path: 'sensors.gnss.enabled', label: 'GNSS Enabled', type: 'boolean' },
    ],
  },
  {
    key: 'controller',
    label: 'Controller',
    fields: [
      { path: 'controller.type', label: 'Controller Type', type: 'enum', options: ['keyboard', 'autopilot'] },
      { path: 'controller.steer_speed', label: 'Steer Speed', type: 'number', step: 0.1 },
      { path: 'controller.throttle_speed', label: 'Throttle Speed', type: 'number', step: 0.1 },
      { path: 'controller.brake_speed', label: 'Brake Speed', type: 'number', step: 0.1 },
    ],
  },
  {
    key: 'vehicle',
    label: 'Vehicle',
    fields: [
      { path: 'vehicle.model', label: 'Model', type: 'string' },
      { path: 'vehicle.mass', label: 'Mass (kg)', type: 'number' },
      { path: 'vehicle.drag_coefficient', label: 'Drag Coefficient', type: 'number', step: 0.01 },
      { path: 'vehicle.max_rpm', label: 'Max RPM', type: 'number' },
    ],
  },
  {
    key: 'display',
    label: 'Display',
    fields: [
      { path: 'display.width', label: 'Width', type: 'number' },
      { path: 'display.height', label: 'Height', type: 'number' },
      { path: 'display.fps', label: 'FPS', type: 'number' },
      { path: 'display.hud_enabled', label: 'HUD Enabled', type: 'boolean' },
      { path: 'display.minimap_enabled', label: 'Minimap Enabled', type: 'boolean' },
    ],
  },
  {
    key: 'analytics',
    label: 'Analytics',
    fields: [
      { path: 'analytics.grafana_base_url', label: 'Grafana Base URL', type: 'string' },
    ],
  },
];

export function getValue(obj, path, fallback = '') {
  return path.split('.').reduce((acc, p) => (acc && acc[p] !== undefined ? acc[p] : fallback), obj);
}

export function setValue(obj, path, value) {
  const keys = path.split('.');
  const clone = { ...obj };
  let ref = clone;
  for (let i = 0; i < keys.length - 1; i++) {
    const k = keys[i];
    ref[k] = typeof ref[k] === 'object' && ref[k] !== null ? { ...ref[k] } : {};
    ref = ref[k];
  }
  ref[keys[keys.length - 1]] = value;
  return clone;
}


