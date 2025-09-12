# EWT Integration

This guide covers deployment of the **Elliott Wave Theory (EWT)** enrichment
service and explains how to keep published payloads compact.

## Service deployment

A dedicated service `mcp-enrichment-ewt` is defined in
`docker-compose.yml`.  It uses the same image as the general enrichment
worker but publishes alerts to the `ewt_alerts` topic and writes data to a
separate Redis database.  Start the service with:

```bash
docker compose up -d mcp-enrichment-ewt
```

### Environment variables

| Variable | Description |
|----------|-------------|
| `EWT_ALERTS_TOPIC` | Redis/Kafka topic used for EWT alerts (default `ewt_alerts`). |
| `EWT_REDIS_URL` | Redis URL for analytic storage. |
| `EWT_ALERTS_REDIS_URL` | Redis URL for pub/sub alerts. |
| `FRACTALS_ONLY` | Set to `true` to publish only fractal data. |
| `WAVE_ONLY` | Set to `true` to publish only Elliott wave data. |

## Selective outputs

`utils.enrichment_engine.publish_ewt_alert` supports toggling between
`fractals_only` and `wave_only` modes to minimize the size of MessagePack
payloads.  When these flags are enabled only the requested section is
serialized and published.

## Payload size checks

Unit tests in `tests/test_ewt_msgpack_payloads.py` verify that selective
outputs remain below a few hundred bytes when serialized with MessagePack.
This helps keep network traffic and Redis storage overhead minimal.
