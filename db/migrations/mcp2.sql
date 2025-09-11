-- Migration: create mcp_docs table with created_at index
CREATE TABLE IF NOT EXISTS mcp_docs (
    id SERIAL PRIMARY KEY,
    doc TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mcp_docs_created_at
    ON mcp_docs (created_at);
