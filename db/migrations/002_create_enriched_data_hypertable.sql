-- Migration: create enriched_data table and hypertable
CREATE TABLE IF NOT EXISTS enriched_data (
    id BIGSERIAL PRIMARY KEY,
    ts TIMESTAMPTZ NOT NULL,
    symbol TEXT,
    payload JSONB NOT NULL
);

SELECT create_hypertable('enriched_data', 'ts', if_not_exists => TRUE);
