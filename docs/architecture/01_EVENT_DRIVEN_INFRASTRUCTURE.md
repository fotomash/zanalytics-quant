# Event-Driven Infrastructure

Kafka and TimescaleDB form the backbone of the data pipeline.

## Kafka
Kafka brokers provide a high-throughput, fault-tolerant bus for real-time data flow. Producers write market events to topics where they are immediately available to consumer services. Partitioning and replication let the stream scale horizontally while preserving ordering guarantees for time-critical processing.

## TimescaleDB
TimescaleDB manages time-series data on top of PostgreSQL. Streams coming from Kafka consumers are stored in hypertables that automatically partition data by time, enabling efficient retention policies, compression, and fast range queries. This makes it suitable for analytics and historical backtests.

## Topology Diagrams

### Event Flow
```mermaid
flowchart LR
    subgraph Producers
        A[Market Feeds]
    end
    A -->|ticks| K[Kafka]
    K -->|consumer groups| C[Stream Processors]
    C -->|hypertable writes| T[(TimescaleDB)]
    T --> U[Analytics & ETL]
```

### Docker Network
```mermaid
flowchart LR
    subgraph data-pipeline
      K2[Kafka] <-->|events| P[Persistence Service]
      P --> T2[(TimescaleDB)]
    end
```

## Deployment Notes
- Services are attached to the isolated `data-pipeline` Docker network to keep traffic separate from other application components.
- `docker-compose.yml` defines `zookeeper`, `kafka`, and `timescaledb` services with persistent volumes such as `timescale-data`.
- A supplemental `docker-compose.kafka.yml` file provides additional Kafka utilities for local development.

## Starting the Services
Use Docker Compose to spin up the core infrastructure:

```bash
docker compose -f docker-compose.yml -f docker-compose.kafka.yml up -d kafka timescaledb
```

The command creates the `data-pipeline` network if it does not exist, starts the Kafka broker, ZooKeeper, and TimescaleDB, and mounts their respective volumes.

## Linking With Future ETL Processes
Future ETL jobs can join the `data-pipeline` network and either subscribe to Kafka topics or read from TimescaleDB:

- To consume from Kafka, configure the job with `KAFKA_BROKERS=kafka:9092` and subscribe to the desired topic.
- To query TimescaleDB, use the connection string `postgresql://postgres:timescale@timescaledb:5432/postgres`.
- Containers run with `--network data-pipeline` will have direct access to both services.
