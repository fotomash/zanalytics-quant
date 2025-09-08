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

