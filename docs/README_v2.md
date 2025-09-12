# Zanalytics Quant v2.0beta Design Overview

This document summarizes the architecture and data flow for the second generation of the Zanalytics Quant platform. It focuses on the stream‑first pipeline, durable memory layers, and the orchestration that binds services together.

## Core Components

- **MT5 Ingress** – dedicated containers push real‑time ticks into the system.
- **Redis Streams & Gears** – aggregate ticks into OHLCV bars and compute rolling indicators for low‑latency access.
- **Kafka Journal** – captures every event for replay, audit, and cross‑service analytics.
- **Postgres (Timescale)** – stores historical bars and positions as the long‑term ledger.
- **MCP Layer** – routes authenticated requests to LLM services and internal APIs.
- **Vector DB** – persists embeddings for retrieval‑augmented generation.

See [architecture_v2.1beta.md](architecture_v2.1beta.md) for diagrams and deeper memory design.

## Data Flow

1. **Ingress** – MT5 adapters publish ticks to Redis Streams and Kafka.
2. **Hot Path** – Redis Gears produces live bars and feature enrichments.
3. **Warm Path** – MCP fetches recent context and vectors before invoking the LLM.
4. **Durable Path** – Kafka topics retain all events; services can replay to rebuild state.
5. **Cold Path** – Batched writers persist data to Postgres for backtesting and compliance.
6. **Egress** – Dashboards and agents subscribe to Redis or query Postgres for decisions and visualization.

For network routing and service topology, consult [architecture.md](architecture.md). Streaming specifics are covered in [architecture_pulse_streaming.md](architecture_pulse_streaming.md).

## Supporting Services

- **Dashboards** – Streamlit and web dashboards visualize live bars and strategy output.
- **Risk & Execution** – Services in `risk_enforcer` and `SRB` consume Kafka and Redis streams to manage trades.
- **Backtesting** – Uses persisted Kafka/Postgres data to simulate strategies under historical conditions. Kafka log replay reconstructs tick-by-tick sequences so simulations remain deterministic and reproducible.
- **Monitoring** – Metrics and alerts are documented in [monitoring.md](monitoring.md).

## Related Documentation

- [JOURNALING.md](JOURNALING.md) – event envelope schema and replay mechanics.
- [vectorization_service.md](vectorization_service.md) – embedding pipeline feeding the vector store.
- [auth.md](auth.md) – MCP authentication and key management.
- [env-plan.md](env-plan.md) – environment variables and deployment references.

This README is the canonical entry point for the v2.0beta architecture. Additional design notes and historical discussions reside in `docs/legacy/`.
