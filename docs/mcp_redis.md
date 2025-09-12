# MCP Redis

Overview of Redis usage within the MCP stack for low-latency agent state, including stream namespaces for per-session data and eviction/durability considerations.

## MCP Redis Memory Windows

This guide clarifies how Redis is used for traditional caching versus MCP memory windows and how it differs from the platform's standard caching layer.

### Standard caching

- Primarily stores high‑velocity tick, bar, and dashboard data.
- Provides low-latency storage for ticks, bars, and other ephemeral data.
- Entries expire quickly and can be reconstructed from upstream feeds.
- Short time‑to‑live (TTL); eviction acceptable; no durability guarantees.
- Shared instance is fine for small/medium loads.

### MCP memory windows

- Dedicated Redis keys retain a rolling window of context for LLM sessions.
- Maintain per-session conversation context for LLMs.
- Larger payloads keyed by session; data may be pinned longer than typical cache entries.
- Supports journal replay so conversations and state can be rebuilt deterministically.
- Windows can be appended to the durable journal for replay or audit.

### Journaling support

- MCP appends events to Redis Streams or lists before mutating memory windows.
- The append-only log provides recovery, auditing, and optional fan-out to Kafka or Postgres.
- Standard cache entries usually skip this step and do not guarantee this durability.

## When to scale out Redis

Start with a single Redis instance for experimentation and light traffic. Split MCP windows to a dedicated Redis node when:

- Active sessions or total window size exceeds ~1 GB.
- Memory pressure or eviction of trading cache would impact latency or correctness.
- Journaling throughput competes with real-time cache traffic or requires disk-backed persistence (AOF/RDB) while caches can remain ephemeral.
- Security or tenancy isolation is needed so production MCP memory does not share an instance with staging caches.
- Long-running memory windows or heavy journaling increase latency for other workloads.

Keeping separate nodes simplifies tuning (e.g., persistence, memory policy) and avoids noisy‑neighbor effects between cache and conversation loads.
