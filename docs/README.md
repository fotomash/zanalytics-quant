Zanalytics Pulse — Documentation Hub
===================================

This repository is migrating from a Redis‑only realtime stack to a dual‑stream
architecture (Redis + Kafka) with durable, replayable journal events. This hub
points to the current sources of truth and clearly marks legacy docs.

- Status taxonomy
  - Active: production direction; maintained
  - Experimental: shadow mode or behind a flag
  - Legacy: kept for history; superseded

Current Direction (Active)
--------------------------

- Architecture (streaming): docs/architecture_pulse_streaming.md
- Journal envelopes and contracts: docs/journal_envelopes.md
- Actions API overview: docs/ACTIONS_API_OVERVIEW.md
- Replay drill quickstart: docs/replay_quickstart.md
- Kafka sidecar quickstart: ops/kafka/quickstart.md
- Pulse runtime (gates + detail API): backend/django/app/nexus/pulse/README.md
- Services (mirror, tick→bar, reconciler): services/README.md
- Dashboard pages index: dashboard/pages/README.md

Legacy / Retired (kept for history)
-----------------------------------

See docs/LEGACY_INDEX.md for a curated list of older guides and one‑liners on
why they’re retired.

Flags and Defaults
------------------

- USE_KAFKA_JOURNAL=false (prod default)
- KAFKA_BROKERS=kafka:9092, PULSE_JOURNAL_TOPIC=pulse.journal
- Data sources (dual): PULSE_BAR_SOURCE=redis|kafka, SCORES_SOURCE=redis|kafka, DECISIONS_SINK=redis|kafka
- Favorites: PULSE_DEFAULT_SYMBOL, baseline: PULSE_BASELINE_EQUITY


Return to [project README](../README.md)
