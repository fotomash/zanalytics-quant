-- Minimal bootstrap for MCP2 Postgres
CREATE TABLE IF NOT EXISTS docs (
  id SERIAL PRIMARY KEY,
  content TEXT
);

