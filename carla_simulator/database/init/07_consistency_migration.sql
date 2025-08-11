-- Consistency and performance migration (idempotent)
-- Safe to run multiple times on existing databases

SET search_path TO carla_simulator;

-- 1) scenarios: add created_at and helpful indexes
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'carla_simulator' AND table_name = 'scenarios' AND column_name = 'created_at'
    ) THEN
        ALTER TABLE scenarios ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
    END IF;
END$$;

-- Indexes for common lookups
CREATE INDEX IF NOT EXISTS idx_scenarios_session_id ON scenarios(session_id);
CREATE INDEX IF NOT EXISTS idx_scenarios_status ON scenarios(status);
CREATE INDEX IF NOT EXISTS idx_scenarios_created_at ON scenarios(created_at);

-- 2) vehicle_data: composite index for time-series reads
CREATE INDEX IF NOT EXISTS idx_vehicle_data_scenario_time ON vehicle_data(scenario_id, timestamp DESC);

-- 3) sensor_data: composite index for time-series reads
CREATE INDEX IF NOT EXISTS idx_sensor_data_scenario_time ON sensor_data(scenario_id, timestamp DESC);

-- 4) simulation_metrics: composite index for time-series reads
CREATE INDEX IF NOT EXISTS idx_sim_metrics_scenario_time ON simulation_metrics(scenario_id, timestamp DESC);

-- 5) users: case-insensitive email lookups
CREATE INDEX IF NOT EXISTS idx_users_email_lower ON users (lower(email));
CREATE INDEX IF NOT EXISTS idx_users_username_lower ON users (lower(username));

-- 6) app_logs: JSONB GIN index for extra field if column exists and is JSONB
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'carla_simulator' AND table_name = 'app_logs' AND column_name = 'extra'
    ) THEN
        BEGIN
            EXECUTE 'CREATE INDEX IF NOT EXISTS idx_app_logs_extra ON app_logs USING gin ((extra))';
        EXCEPTION WHEN others THEN
            -- ignore if column type is not JSONB or index exists in another form
            NULL;
        END;
    END IF;
END$$;

-- 7) Ensure tenant_configs active uniqueness is present
CREATE UNIQUE INDEX IF NOT EXISTS uq_active_config_per_tenant 
ON tenant_configs(tenant_id) WHERE is_active = TRUE;

-- 8) Permissions: ensure carla_user has access
DO $$
BEGIN
    PERFORM 1 FROM pg_roles WHERE rolname = 'carla_user';
    IF FOUND THEN
        GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA carla_simulator TO carla_user;
        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA carla_simulator TO carla_user;
    END IF;
END$$;

-- 9) Split tenant_configs into app_config and sim_config while keeping legacy config
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'carla_simulator' AND table_name='tenant_configs' AND column_name='app_config'
    ) THEN
        ALTER TABLE tenant_configs ADD COLUMN app_config JSON NULL;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'carla_simulator' AND table_name='tenant_configs' AND column_name='sim_config'
    ) THEN
        ALTER TABLE tenant_configs ADD COLUMN sim_config JSON NULL;
    END IF;
END $$;

-- 10) Backfill from legacy config for existing rows (best-effort)
UPDATE tenant_configs
SET app_config = COALESCE(app_config, (config::jsonb - 'server' - 'world' - 'simulation' - 'sensors' - 'controller' - 'vehicle' - 'scenarios')::json),
    sim_config = COALESCE(sim_config, config)
WHERE TRUE;

-- 11) CARLA metadata table for catalogs (maps, blueprints, enums)
CREATE TABLE IF NOT EXISTS carla_metadata (
    id SERIAL PRIMARY KEY,
    version VARCHAR(32) NOT NULL UNIQUE,
    data JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_carla_metadata_version ON carla_metadata(version);

-- 12) Convenience view for active tenant configs (split + legacy)
CREATE OR REPLACE VIEW v_active_tenant_configs AS
SELECT tenant_id, version, is_active, config, app_config, sim_config
FROM tenant_configs
WHERE is_active = TRUE;

-- 13) Stored procedures for CARLA metadata
CREATE OR REPLACE FUNCTION carla_metadata_upsert(v TEXT, d JSON)
RETURNS VOID AS $$
INSERT INTO carla_metadata (version, data, created_at, updated_at)
VALUES (v, d, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT (version)
DO UPDATE SET data = EXCLUDED.data, updated_at = CURRENT_TIMESTAMP;
$$ LANGUAGE SQL;

CREATE OR REPLACE FUNCTION get_carla_metadata(v TEXT)
RETURNS JSON AS $$
SELECT data FROM carla_metadata WHERE version = v;
$$ LANGUAGE SQL;


