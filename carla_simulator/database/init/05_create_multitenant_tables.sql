-- Connect to the carla_simulator database and set the schema
SET search_path TO carla_simulator;

-- Create tenants table
CREATE TABLE IF NOT EXISTS tenants (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) UNIQUE NOT NULL,
    slug VARCHAR(150) UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create tenant_configs table to store full simulator config JSON per tenant
CREATE TABLE IF NOT EXISTS tenant_configs (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    version INTEGER NOT NULL DEFAULT 1,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    config JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Ensure only one active config per tenant
CREATE UNIQUE INDEX IF NOT EXISTS uq_active_config_per_tenant 
ON tenant_configs(tenant_id) WHERE is_active = TRUE;

-- Helpful indexes
CREATE INDEX IF NOT EXISTS idx_tenant_configs_tenant_id ON tenant_configs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tenant_configs_created_at ON tenant_configs(created_at);

-- Seed a default tenant if not exists
INSERT INTO tenants (name, slug, is_active)
VALUES ('Default Tenant', 'default', TRUE)
ON CONFLICT (slug) DO NOTHING;


