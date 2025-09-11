# Event-Driven Infrastructure

## Kafka
Kafka provides the central message bus for the analytics platform. Services publish market ticks and other events to Kafka topics, and downstream consumers build aggregates or trigger trading logic. This decoupled event log allows components to scale independently and ensures reliable delivery of streaming data.

## TimescaleDB
TimescaleDB extends PostgreSQL with native time-series capabilities. Kafka consumers can persist high‑volume price or signal streams into TimescaleDB, where hypertables enable efficient retention policies, compression, and fast queries across time ranges. This makes it well suited for analytics and historical research.

Kafka and TimescaleDB run on the dedicated `data-pipeline` network alongside future ETL orchestration tools.
