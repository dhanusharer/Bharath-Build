-- Local PostgreSQL Initialization Script
-- Multimodal Medication Accessibility System

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Health verification table for container readiness checks
CREATE TABLE IF NOT EXISTS system_health_probe (
    id SERIAL PRIMARY KEY,
    probe_name VARCHAR(50) NOT NULL,
    last_ping TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO system_health_probe (probe_name) 
VALUES ('initial_scaffold_probe')
ON CONFLICT DO NOTHING;
