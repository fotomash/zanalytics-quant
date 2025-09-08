# Kafka (Redpanda) Quickstart

This stack runs Redpanda (Kafka API–compatible) as a sidecar for dark traffic.

## Bring up the broker

```
docker compose -f docker-compose.yml -f docker-compose.kafka.yml up -d
```

Verify broker health (host port 29092):

```
rpk cluster info --brokers=localhost:29092
```

## Journal smoke test

Keep journal disabled by default:

```
export USE_KAFKA_JOURNAL=false
```

Flip in staging only to validate, then flip back:

```
export USE_KAFKA_JOURNAL=true
# exercise your flow to emit score/decision events
```

Consume a few events:

```
rpk topic consume pulse.journal -n 5 --brokers=localhost:29092
# or
kcat -b localhost:29092 -t pulse.journal -C -o -5 -q
```

## Redis → Kafka mirror

The mirror subscribes to Redis Pub/Sub pattern `ticks.*` and produces to identical Kafka topics.

Configure via env:

- `REDIS_URL=redis://redis:6379/0`
- `TICKS_PATTERN=ticks.*`
- `KAFKA_BROKERS=kafka:9092`

## Kafka tick → bar service (shadow mode)

Consumes `ticks.<SYMBOL>`, produces `bars.<SYMBOL>.1m` with simple minute aggregation.

Environment:

- `KAFKA_BROKERS=kafka:9092`
- `TICKS_TOPIC=ticks.BTCUSDT`
- `BARS_TOPIC=bars.BTCUSDT.1m`
- `KAFKA_GROUP=bars-1m-builder`

## Rollback

- Stop the additional services: `docker compose stop kafka kafka-tick-to-bar redis-to-kafka-mirror`
- Set `USE_KAFKA_JOURNAL=false`

---

## WS-4 Finalize: Nightly Parity & Ops Profile

We ship a Compose profile `ops` with a one-shot reconciler that compares Kafka bars
to Redis bars and exits non-zero if parity falls below 99.9%.

Run locally:

```
docker compose -f docker-compose.yml -f docker-compose.kafka.yml --profile ops up bars-reconcile --build --abort-on-container-exit
```

Environment knobs:

- `BARS_TOPIC` (default `bars.BTCUSDT.1m`)
- `REDIS_BARS_KEY` (default `bars:BTCUSDT:1m`)
- `WINDOW_BARS` (default `1440`, i.e., last 24h)
- `KAFKA_BROKERS` (default `kafka:9092`)

CI suggestion: add a nightly job:

```
docker compose -f docker-compose.yml -f docker-compose.kafka.yml --profile ops up bars-reconcile \
  --abort-on-container-exit --exit-code-from bars-reconcile
```

Notes

- Redpanda image: `redpandadata/redpanda:v23.3.10`
- Compose warning fixed: removed obsolete `version:` key
- Container pip warning silenced via `ENV PIP_ROOT_USER_ACTION=ignore`

---

## Sanity checklist (staging)

1) Rebuild Django (pins + Dockerfile):

```
docker compose build django
docker compose up -d django
```

2) Bring up Kafka sidecar & services:

```
docker compose -f docker-compose.yml -f docker-compose.kafka.yml up -d
```

3) Smoke the broker:

```
rpk cluster info --brokers=localhost:29092
```

4) Keep journal disabled first (no-op path). Verify nothing changes functionally. Flip `USE_KAFKA_JOURNAL=true` temporarily and check:

```
rpk topic consume pulse.journal -n 5 --brokers=localhost:29092
```

Then set it back to false for dark mode.

5) Run parity job on-demand:

```
docker compose -f docker-compose.yml -f docker-compose.kafka.yml --profile ops up bars-reconcile \
  --abort-on-container-exit --exit-code-from bars-reconcile
```
