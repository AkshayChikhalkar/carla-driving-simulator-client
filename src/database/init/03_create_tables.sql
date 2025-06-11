-- Connect to the carla_simulator database and set the schema
SET search_path TO carla_simulator;

CREATE TABLE IF NOT EXISTS scenarios (
    scenario_id SERIAL PRIMARY KEY,
    session_id UUID NOT NULL,
    scenario_name VARCHAR NOT NULL,
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    status VARCHAR,
    scenario_metadata JSONB
);

CREATE TABLE IF NOT EXISTS vehicle_data (
    id SERIAL PRIMARY KEY,
    scenario_id INTEGER REFERENCES scenarios(scenario_id) ON DELETE CASCADE,
    session_id UUID NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    position_x FLOAT,
    position_y FLOAT,
    position_z FLOAT,
    velocity FLOAT,
    acceleration FLOAT,
    steering_angle FLOAT,
    throttle FLOAT,
    brake FLOAT
);

CREATE TABLE IF NOT EXISTS sensor_data (
    id SERIAL PRIMARY KEY,
    scenario_id INTEGER REFERENCES scenarios(scenario_id) ON DELETE CASCADE,
    session_id UUID NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sensor_type VARCHAR,
    data JSONB
);

CREATE TABLE IF NOT EXISTS simulation_metrics (
    id SERIAL PRIMARY KEY,
    scenario_id INTEGER REFERENCES scenarios(scenario_id) ON DELETE CASCADE,
    session_id UUID NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    elapsed_time FLOAT,
    speed FLOAT,
    position_x FLOAT,
    position_y FLOAT,
    position_z FLOAT,
    throttle FLOAT,
    brake FLOAT,
    steer FLOAT,
    target_distance FLOAT,
    target_heading FLOAT,
    vehicle_heading FLOAT,
    heading_diff FLOAT,
    acceleration FLOAT,
    angular_velocity FLOAT,
    gear INTEGER,
    hand_brake BOOLEAN,
    reverse BOOLEAN,
    manual_gear_shift BOOLEAN,
    collision_intensity FLOAT,
    cloudiness FLOAT,
    precipitation FLOAT,
    traffic_count INTEGER,
    fps FLOAT,
    event VARCHAR,
    event_details VARCHAR,
    rotation_x FLOAT,
    rotation_y FLOAT,
    rotation_z FLOAT
); 