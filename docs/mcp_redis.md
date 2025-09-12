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

