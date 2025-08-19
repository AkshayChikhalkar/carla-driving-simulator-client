-- Set schema
SET search_path TO carla_simulator;

-- Logs table to capture application logs per tenant
CREATE TABLE IF NOT EXISTS app_logs (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id) ON DELETE SET NULL,
    level VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    extra JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_app_logs_tenant_id_created_at
ON app_logs(tenant_id, created_at DESC);

-- Reports table to store generated HTML reports
CREATE TABLE IF NOT EXISTS simulation_reports (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    html TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sim_reports_tenant_id_created_at
ON simulation_reports(tenant_id, created_at DESC);


