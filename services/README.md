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

MCP2
----

FastAPI service for capturing `StrategyPayloadV1` trade payloads in Redis and searching indexed documents stored in Postgres.

Key endpoints:

- `GET /health` — service health check
- `POST /log_enriched_trade` — persist a `StrategyPayloadV1` payload and enqueue its ID
- `GET /search_docs?query=<text>` — search indexed docs
- `GET /fetch_payload?id=<id>` — retrieve a stored payload by ID
- `GET /trades/recent?limit=<n>` — list recent trade payloads

For operational details, see the [mcp2 runbook](../docs/runbooks/mcp2.md).

Telegram Bot
------------

Build and run the Telegram service:

```
docker compose -f services/docker-compose.yml up telegram
```

Ensure the following environment variables are set before starting:

- `KAFKA_BROKER` – address of the Kafka broker (default `kafka:9092`)
- `TELEGRAM_BOT_TOKEN` – token for your Telegram bot
- `TELEGRAM_CHAT_ID` – destination chat ID for messages

