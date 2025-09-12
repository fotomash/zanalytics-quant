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

<!-- TOC -->
- [Current Direction (Active)](#current-direction-active)
- [Legacy / Retired (kept for history)](#legacy-retired-kept-for-history)
- [Flags and Defaults](#flags-and-defaults)
- [Static Info Site](#static-info-site)
<!-- /TOC -->

Current Direction (Active)
--------------------------

- [Architecture (streaming)](architecture_pulse_streaming.md)
- [Tick stream v2 migration notes](tick_stream_v2_migration.md)
- [Journal envelopes and contracts](journal_envelopes.md)
- [Actions API overview](ACTIONS_API_OVERVIEW.md)
- [Kafka sidecar quickstart](../ops/kafka/quickstart.md)
- [Pulse runtime (gates + detail API)](../backend/django/app/nexus/pulse/README.md)
- [Services (mirror, tick→bar, reconciler)](../services/README.md)
- [Dashboard pages index](../dashboard/pages/README.md)
- [Dashboard app](../dashboard/README.md)
- [Prototype dashboards](../dashboards/README.md)
- [Monitoring stack](monitoring.md)
- [MCP2 connector config](connectors/mcp2_connector.yaml) – dev/prod SSE endpoints
- [MCP2 OpenAI tools manifest](connectors/actions_openai_mcp2.yaml)
- [MCP2 runbook](runbooks/mcp2.md)

Legacy / Retired (kept for history)
-----------------------------------

Older guides remain in this directory for historical reference and are no longer maintained.

Flags and Defaults
------------------

- USE_KAFKA_JOURNAL=false (prod default)
- KAFKA_BROKERS=kafka:9092, PULSE_JOURNAL_TOPIC=pulse.journal
- Data sources (dual): PULSE_BAR_SOURCE=redis|kafka, SCORES_SOURCE=redis|kafka, DECISIONS_SINK=redis|kafka
- Favorites: PULSE_DEFAULT_SYMBOL, baseline: PULSE_BASELINE_EQUITY
- Redis settings: REDIS_URL=redis://redis:6379/0,
  PULSE_JOURNAL_PATH=/app/data/journal
- Vector DB: VECTOR_DB_URL=http://qdrant:6333,
  QDRANT_API_KEY=<token>
- Local inference: LOCAL_LLM_MODEL=llama3:8b-instruct

See the [Environment Variables](../README.md#environment-variables)
section of the project README for descriptions and additional options.


Static Info Site
----------------

- The public info site is a static hub synced directly from this repository's `docs/` directory.
- Deploy by serving the static content via tools like Streamlit or MkDocs behind Traefik.
- Streamlit setup details are in [streamlit.md](streamlit.md).

> Editing any `docs/*.md` file and pushing changes updates the live site within seconds. See [info-site.md](info-site.md) for details on content sourcing, deployment, and auto-sync.

Return to [project README](../README.md)


## Quickstart

Run this:

Use the main `docker-compose.yml` and optional `docker-compose.override.yml` for local overrides.
Legacy compose files live under `docs/legacy/`.

```bash
docker compose up
```

## Action manifest checks

Keep the OpenAI Actions manifest in sync with the MCP server and smoke‑test the endpoints:

```bash
python scripts/verify_actions.py
python scripts/test_actions.py
```

More details are in [openai-actions.md](openai-actions.md).
