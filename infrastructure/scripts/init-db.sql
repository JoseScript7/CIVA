-- CIVA Platform — TimescaleDB Initialization
-- Creates tables and hypertables for behavioral data storage

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- ============================================================
-- User Behavioral Baselines
-- ============================================================
CREATE TABLE IF NOT EXISTS user_baselines (
    id              BIGSERIAL,
    user_id         TEXT NOT NULL,
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    feature_vector  DOUBLE PRECISION[25],
    risk_score      DOUBLE PRECISION,
    session_id      TEXT,
    anomaly_flags   JSONB DEFAULT '[]'::jsonb,
    anomaly_category TEXT DEFAULT 'normal',
    model_version   TEXT,
    inference_time_us BIGINT,
    
    PRIMARY KEY (timestamp, id)
);

-- Convert to hypertable for time-series optimization
SELECT create_hypertable('user_baselines', 'timestamp', 
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Index for fast user lookups
CREATE INDEX IF NOT EXISTS idx_user_baselines_user_id 
    ON user_baselines (user_id, timestamp DESC);

-- Index for high-risk event queries
CREATE INDEX IF NOT EXISTS idx_user_baselines_high_risk 
    ON user_baselines (risk_score DESC, timestamp DESC) 
    WHERE risk_score > 60;

-- ============================================================
-- Continuous Aggregate: Hourly User Baseline
-- ============================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS user_baseline_hourly
WITH (timescaledb.continuous) AS
SELECT
    user_id,
    time_bucket('1 hour', timestamp) AS bucket,
    AVG(risk_score) AS avg_risk,
    MAX(risk_score) AS max_risk,
    MIN(risk_score) AS min_risk,
    STDDEV(risk_score) AS stddev_risk,
    COUNT(*) AS event_count
FROM user_baselines
GROUP BY user_id, bucket
WITH NO DATA;

-- Refresh policy: refresh every hour, cover last 2 hours
SELECT add_continuous_aggregate_policy('user_baseline_hourly',
    start_offset => INTERVAL '2 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

-- ============================================================
-- Session Events Log
-- ============================================================
CREATE TABLE IF NOT EXISTS session_events (
    id              BIGSERIAL,
    event_id        TEXT NOT NULL,
    session_id      TEXT NOT NULL,
    user_id         TEXT NOT NULL,
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    client_ip       TEXT,
    geo_country     TEXT,
    geo_city        TEXT,
    device_fp       TEXT,
    request_path    TEXT,
    http_method     TEXT,
    risk_score      DOUBLE PRECISION,
    action_taken    TEXT,
    
    PRIMARY KEY (timestamp, id)
);

SELECT create_hypertable('session_events', 'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_session_events_session 
    ON session_events (session_id, timestamp DESC);

-- ============================================================
-- Attack Reports
-- ============================================================
CREATE TABLE IF NOT EXISTS attack_reports (
    id              BIGSERIAL PRIMARY KEY,
    report_id       TEXT UNIQUE NOT NULL,
    session_id      TEXT NOT NULL,
    user_id         TEXT,
    attack_type     TEXT NOT NULL,
    severity        TEXT NOT NULL,
    confidence      DOUBLE PRECISION,
    mitre_ids       TEXT[],
    iocs            JSONB DEFAULT '[]'::jsonb,
    timeline        JSONB DEFAULT '[]'::jsonb,
    recommendations TEXT[],
    forensic_url    TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_attack_reports_type 
    ON attack_reports (attack_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_attack_reports_severity 
    ON attack_reports (severity, created_at DESC);

-- ============================================================
-- Data Retention Policy: Auto-delete data older than 90 days
-- ============================================================
SELECT add_retention_policy('user_baselines', INTERVAL '90 days', if_not_exists => TRUE);
SELECT add_retention_policy('session_events', INTERVAL '90 days', if_not_exists => TRUE);

-- ============================================================
-- Compression Policy: Compress data older than 7 days
-- ============================================================
ALTER TABLE user_baselines SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'user_id'
);
SELECT add_compression_policy('user_baselines', INTERVAL '7 days', if_not_exists => TRUE);

ALTER TABLE session_events SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'session_id'
);
SELECT add_compression_policy('session_events', INTERVAL '7 days', if_not_exists => TRUE);
