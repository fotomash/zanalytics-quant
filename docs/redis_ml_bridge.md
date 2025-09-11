# Redis ML Bridge

Publish machine learning signals into Redis streams for downstream consumers.

## Startup

```bash
python services/redis_ml_bridge.py
```

Environment variables:

- `REDIS_HOST` (default `localhost`)
- `REDIS_PORT` (default `6379`)
- `STREAM_VERSION` (default `1`)
- `ML_SIGNAL_STREAM` (default `ml:signals:v<STREAM_VERSION>`)
- `ML_RISK_STREAM` (default `ml:risk:v<STREAM_VERSION>`)

## Payload schema

Signals published to `ML_SIGNAL_STREAM` (e.g. `ml:signals:v1`) follow this structure:

```json
{
  "symbol": "EURUSD",
  "risk": 0.12,
  "alpha": 0.05,
  "confidence": 0.87,
  "timestamp": 1700000000.0
}
```

A reduced payload containing just `symbol`, `risk`, and `timestamp` is also added to `ML_RISK_STREAM` (e.g. `ml:risk:v1`).

## Integration

Use `RedisMLBridge.publish()` inside model pipelines to forward their outputs:

```python
from services.redis_ml_bridge import RedisMLBridge

bridge = RedisMLBridge()
bridge.publish(symbol, risk, alpha, confidence)
```

Docker users can run the `redis-ml-bridge` service defined in `docker-compose.yml` to stream signals automatically.
