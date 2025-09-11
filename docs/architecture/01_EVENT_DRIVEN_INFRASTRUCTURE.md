# Event-Driven Infrastructure

Kafka and TimescaleDB form the backbone of the data pipeline.

## Kafka
Kafka brokers provide a high-throughput, fault-tolerant bus for real-time data flow. Producers write market events to topics where they are immediately available to consumer services. Partitioning and replication let the stream scale horizontally while preserving ordering guarantees for time-critical processing.

## TimescaleDB
TimescaleDB manages time-series data on top of PostgreSQL. Streams coming from Kafka consumers are stored in hypertables that automatically partition data by time, enabling efficient retention policies, compression, and fast range queries. This makes it suitable for analytics and historical backtests.

## Data-Pipeline Network and Service Roles
Both services run on the isolated `data-pipeline` Docker network. Kafka's service responsibility is to ingest and distribute event streams, acting as the system's message backbone. TimescaleDB's service responsibility is to persist and serve time-series records to downstream analytics and ETL jobs. Attaching them to a dedicated network isolates data transport from application traffic while allowing ETL tools to join the same network for secure access.
