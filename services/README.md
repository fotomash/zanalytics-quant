Services (Experimental/Shadows)
===============================

Mirror & Bars (shadow mode)
---------------------------

- `redis_to_kafka_mirror.py` — mirrors Redis pub/sub `ticks.*` to Kafka topics (same names)
- `kafka_tick_to_bar.py` — consumes `ticks.<SYMBOL>`, produces `bars.<SYMBOL>.1m`
- `bars_reconcile.py` — compares Kafka bars vs Redis bars for parity

Dockerfiles
-----------

- `Dockerfile.mirror` — mirror image
- `Dockerfile.bars` — bar builder image

Compose
-------

See `docker-compose.yml` for Kafka and service definitions.

Status
------

- Experimental/shadow mode until parity passes (≥99.9% for 5 trading days)

Enrichment Worker
-----------------

Consumes tick data from Redis Streams and persists enriched ticks to Postgres.

```
python services/enrichment/worker.py
```

Required environment variables:

- `PG_DSN` – PostgreSQL DSN for persistence (must be provided via environment variable or configuration file)

MCP2
----

FastAPI service for capturing `StrategyPayloadV1` trade payloads in Redis and searching indexed documents stored in Postgres.

Key endpoints:

- `GET /health` — service health check
- `POST /log_enriched_trade` — persist a `StrategyPayloadV1` payload and enqueue its ID
- `GET /search_docs?query=<text>` — search indexed docs
- `GET /fetch_payload?id=<id>` — retrieve a stored payload by ID
- `GET /trades/recent?limit=<n>` — list recent trade payloads
- `POST /llm/whisperer` — guidance with behavioral nudges
- `POST /llm/simple` — baseline guidance without behavioral nudges
- `POST /llm/{model}/analyze` — analyze latest stream payload via selected model

For operational details, see the [mcp2 runbook](../docs/runbooks/mcp2.md).

Discord Bot
-----------

Build and run the Discord bot service:

```
docker compose up pulse-bot
```

Source code lives at [`services/pulse_bot/bot.py`](pulse_bot/bot.py).

Ensure the following environment variables are set before starting:

- `DISCORD_BOT_TOKEN` – token for your Discord bot
- `DISCORD_CHANNEL_WHITELIST` – optional comma‑separated list of allowed channel IDs


Vectorization Service
---------------------

Consumes `final-analysis-payloads` messages and writes embeddings to an external vector database.

```
docker compose up vectorization-service
```

Overseer
--------

Simple consumer that logs messages from a Kafka topic.

Start the service:

```
docker compose up overseer
```

Required environment variables:

- `KAFKA_BOOTSTRAP_SERVERS` – Kafka brokers (default `kafka:9092`)
- `KAFKA_GROUP_ID` – consumer group (default `vectorization-service`)
- `KAFKA_ANALYSIS_TOPIC` – topic to consume (default `final-analysis-payloads`)
- `QDRANT_URL` – base URL for the vector database
- `QDRANT_API_KEY` – API key used for authentication

See [docs/vectorization_service.md](../docs/vectorization_service.md) for complete details.
- `KAFKA_BOOTSTRAP_SERVERS` – address of the Kafka broker (default `kafka:9092`)
- `OVERSEER_TOPIC` – Kafka topic to consume (default `overseer-events`)

