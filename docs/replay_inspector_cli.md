# Replay Inspector CLI

`ops/kafka/replay_consumer.py` replays Kafka topics for inspection, backfills, or quick metrics.

## Usage

```bash
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
export KAFKA_TOPIC=ticks.BTCUSDT
python ops/kafka/replay_consumer.py --start-offset 0 --batch-size 100
```

### Modes

- `simple` – print each message (default)
- `batch` – forward the entire poll to a custom sink
- `harmonic` – compute P&L and expose Prometheus metrics (`--metrics-port`)

Environment variables mirror the CLI flags:
`KAFKA_TOPIC`, `KAFKA_START_OFFSET`, `KAFKA_BATCH_SIZE`, `KAFKA_CONSUMER_MODE`, `KAFKA_BOOTSTRAP_SERVERS`.

## Inspecting Output

Run in harmonic mode and scrape metrics:

```bash
python ops/kafka/replay_consumer.py --mode harmonic --metrics-port 9100
```

The CLI exits when the topic is exhausted or when no new messages arrive before the timeout.
