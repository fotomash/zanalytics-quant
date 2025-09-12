# MCP Redis

Guides Redis usage within the MCP layer for low-latency agent state.

- Stream namespaces for per-session data
- Eviction and durability notes
MCP Redis Memory Windows
========================

This guide clarifies how Redis is used for traditional caching
versus MCP memory windows and when to grow beyond a single
instance.

Standard caching
----------------

* **Purpose:** low‑latency storage for ticks, bars and other
  ephemeral data.
* **Traits:** short time‑to‑live (TTL), eviction acceptable, no
  durability guarantees.
* **Topology:** shared instance is fine for small/medium loads.

MCP memory windows
------------------

* **Purpose:** maintain per‑session conversation context for LLMs.
* **Traits:** larger payloads, keyed by session, may pin data in
  memory longer than typical cache entries.
* **Journaling:** windows can be appended to the durable journal
  so context can be replayed or audited. Standard cache entries
  usually skip this step.

Scaling guidance
----------------

Split MCP windows to a dedicated Redis when:

* active sessions or total window size exceeds ~1 GB
* eviction of trading cache would impact latency or correctness
* journaling throughput competes with real‑time cache traffic

Keep a single instance when traffic is light and memory pressure
is low. Separate nodes simplify tuning (e.g., persistence,
memory policy) and avoid noisy‑neighbor effects between cache
and conversation loads.

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
