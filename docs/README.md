Zanalytics Pulse — Documentation Hub
===================================

This repository is migrating from a Redis‑only realtime stack to a dual‑stream
architecture (Redis + Kafka) with durable, replayable journal events. This hub
points to the current sources of truth and clearly marks legacy docs.

> **Note:** The [Actions Tracker](actions-tracker.md) is the canonical source for action status and links. When updating actions, keep schemas, implementation code, and documentation in sync with the tracker.

- Status taxonomy
  - Active: production direction; maintained
  - Experimental: shadow mode or behind a flag
  - Legacy: kept for history; superseded

Current Direction (Active)
--------------------------

- Architecture (streaming): docs/architecture_pulse_streaming.md
- Journal envelopes and contracts: docs/journal_envelopes.md
- Actions API overview: docs/ACTIONS_API_OVERVIEW.md
- Kafka sidecar quickstart: ops/kafka/quickstart.md
- Pulse runtime (gates + detail API): backend/django/app/nexus/pulse/README.md
- Services (mirror, tick→bar, reconciler): services/README.md
- Dashboard pages index: dashboard/pages/README.md
- Monitoring stack: docs/monitoring.md

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


Static Info Site
----------------

- The public info site is a static hub synced directly from this repository's `docs/` directory.
- No WordPress backend or other dynamic CMS is involved.
- Deploy by serving the static content via tools like Streamlit or MkDocs behind Traefik.
- Streamlit setup details are in [streamlit.md](streamlit.md).

> Editing any `docs/*.md` file and pushing changes updates the live site within seconds. See [info-site.md](info-site.md) for details on content sourcing, deployment, and auto-sync.

Return to [project README](../README.md)

