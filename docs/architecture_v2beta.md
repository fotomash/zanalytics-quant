# Architecture v2 Beta

This document elaborates on the memory design introduced in the v2 beta of Zanalytics Quant.

## MCP Redis
High-speed cache and event bus for ticks, bars, and agent state. It coordinates MCP requests and real-time updates.

See [redis_architecture/README.md](../redis_architecture/README.md) for deployment and topology details.

## Journal Persistence
Durable event journal backed by Kafka and Postgres enables replay, audits, and behavioral analytics.

Schemas and integration notes live in [JOURNALING.md](JOURNALING.md).

## Vector Memory
Embeddings from the analysis pipeline are stored in an external vector database for long-term recall and search.

The ingestion service is described in [vectorization_service.md](vectorization_service.md).
