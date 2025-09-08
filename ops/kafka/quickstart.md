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

