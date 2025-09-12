# MCP Redis

Overview of Redis usage within the MCP stack for low-latency message passing and ephemeral state. Details configuration and connection patterns for memory-centric workflows.
# MCP Redis Memory Windows

This guide explains how the Model Control Plane (MCP) uses Redis and how it differs from the platform's standard caching layer.

## Key distinctions

### Standard caching
- Primarily stores high‑velocity tick, bar, and dashboard data.
- Entries expire quickly and can be reconstructed from upstream feeds.
- Optimized for throughput and low latency over durability.

### MCP memory windows
- Dedicated Redis keys retain a rolling window of context for LLM sessions.
- Data is pinned for the lifetime of a session rather than expiring immediately.
- Supports journal replay so that conversations and state can be rebuilt deterministically.

### Journaling support
- MCP appends events to Redis Streams or lists before mutating memory windows.
- The append‑only log provides recovery, auditing, and optional fan‑out to Kafka or Postgres.
- Standard caches do **not** guarantee this durability.

## When to scale out Redis
Start with a single Redis instance for experimentation. Scale to separate instances when:

- **Memory pressure** – tick/bar caches compete with MCP session data.
- **Different persistence needs** – journaling requires disk‑backed AOF/RDB while caches can stay ephemeral.
- **Security or tenancy isolation** – production MCP memory should not share an instance with staging caches.
- **Performance** – long‑running memory windows or heavy journaling increase latency for other workloads.

Splitting workloads across dedicated Redis nodes keeps the MCP responsive while leaving room for traditional caching and analytics jobs.
