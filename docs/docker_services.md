# Docker Compose Services

The v2.1beta stack introduces several services to the Docker compose file. The table below summarises each service, its key environment variables, and startup order.

| Service | Purpose | Key Environment Variables | Startup Order |
| --- | --- | --- | --- |
| `caching` | Caches enriched analysis payloads in Redis and exposes an optional metrics endpoint. | `KAFKA_BROKERS`, `KAFKA_GROUP`, `KAFKA_TOPIC`, `REDIS_HOST`, `REDIS_PORT`, `LATEST_PAYLOAD_TTL`, `ACTIVE_FVG_TTL`, `BEHAVIORAL_SCORE_TTL` | Waits for `kafka` to start and `redis` to become healthy. |
| `overseer` | Listens to Kafka events for supervisory actions. | `KAFKA_BOOTSTRAP_SERVERS`, `OVERSEER_TOPIC` | Starts after `kafka`. |
| `qdrant` | Vector database backing long-term memory. | – | Independent, but other services depend on it. |
| `vectorization-service` | Consumes analysis payloads and writes embeddings to Qdrant. | `KAFKA_BOOTSTRAP_SERVERS`, `KAFKA_GROUP_ID`, `KAFKA_ANALYSIS_TOPIC`, `QDRANT_URL`, `QDRANT_API_KEY` | Requires `kafka` and `qdrant`. |
| `ollama` | Hosts local language models used by the pipeline. | `OLLAMA_KEEP_ALIVE` | No dependencies. |

Services connect to the shared `data-pipeline` network when they exchange Kafka messages or store embeddings, ensuring predictable startup sequencing and communication.
