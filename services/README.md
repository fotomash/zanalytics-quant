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

See `docker-compose.kafka.yml` for Redpanda and service definitions.

Status
------

- Experimental/shadow mode until parity passes (≥99.9% for 5 trading days)

MCP2
----

FastAPI service that logs `StrategyPayloadV1` trade payloads to Redis and supports document search in Postgres.

Key endpoints:

- `GET /health` — service health check
- `POST /log_enriched_trade` — store a `StrategyPayloadV1` trade payload
- `GET /search_docs?query=<text>` — search indexed docs
- `GET /fetch_payload?id=<id>` — retrieve a stored payload by ID
- `GET /trades/recent?limit=<n>` — list recent trade payloads

For operational details, see [docs/runbooks/mcp2.md](../docs/runbooks/mcp2.md).

