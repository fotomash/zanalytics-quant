Pulse Streaming Architecture (Active)
====================================

Goal: run Redis (current) and Kafka (new) side‑by‑side, adding durability and
replay without breaking existing clients.

Core flows
----------

- Ticks: MT5/bridge → Redis (pub/sub) → (mirror) → Kafka `ticks.<SYMBOL>`
- Bars: (current) Redis bar builder • (shadow) Kafka bars service → `bars.<SYMBOL>.1m`
- Pulse gates: Django `nexus/pulse` loads bars (DB/bridge), computes Structure/Liquidity/Risk, exposes `/api/v1/feed/pulse-status|pulse-detail`
- Journal: PulseKernel emits envelopes to Kafka `pulse.journal` (feature‑flagged)

Feature flags
-------------

- USE_KAFKA_JOURNAL=false (prod default)
- PULSE_BAR_SOURCE=redis|kafka (migration lever after parity passes)
- SCORES_SOURCE, DECISIONS_SINK — reserved for later migrations

Services
--------

- services/redis_to_kafka_mirror.py — mirrors Redis pub/sub ticks to Kafka
- services/kafka_tick_to_bar.py — aggregates 1m bars from Kafka ticks (shadow)
- services/bars_reconcile.py — nightly parity validation (OHLC within 1 tick, volume tol)

Acceptance gates
----------------

1) 24h hygiene green; compose healthchecks passing
2) Journal ON in staging → topic contains expected events; OFF by default
3) Bars parity ≥99.9% for 5 trading days
4) Flip PULSE_BAR_SOURCE to kafka in staging → then prod

Rollback
--------

- Stop sidecar services; reset flags to Redis. No API changes to clients.

