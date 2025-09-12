# News Buffer

## Overview
Macro and high‑impact news events are buffered so analyzers and risk engines can avoid trading during periods of elevated volatility.  Events are ingested from external calendars, stored in Redis, and aged out once they are no longer relevant.  Consumers query the buffer to determine whether a frame should be blocked or if confidence scores must be clamped.

## Data schema
Events are kept as JSON objects in a Redis sorted set keyed by event time.

```json
{
  "id": "nfp-2024-11",
  "source": "forexfactory",
  "title": "Non‑Farm Payrolls",
  "timestamp": "2024-11-08T13:30:00Z",
  "impact": "high",
  "tags": ["usd", "labor"],
  "created_at": "2024-11-01T00:00:00Z"
}
```

The sorted set uses the unix timestamp as the score so range queries over time windows are efficient.

## Retention strategy
- Events older than the current time are automatically evicted using `ZREMRANGEBYSCORE`.
- Each event is stored with a configurable buffer window (default ±30 minutes) to block trading before and after the release.
- A background job prunes any event whose timestamp is more than 24 hours in the past to keep the set small.

## Integration points
- **Enrichment engine** – attaches a `news_active` flag and reason string to incoming frames by checking whether the frame timestamp falls inside a buffered window.
- **Risk processors** – `risk_enforcer` and other guards use the flag to reject or resize orders during major releases.
- **Analytics** – components such as the Wyckoff scorer clamp logits when the buffer is active, reducing false signals.

## Usage examples
### Publishing an event
```python
import json, redis, datetime as dt
r = redis.Redis()
event = {
    "id": "cpi-2024-12",
    "source": "forexfactory",
    "title": "CPI",
    "timestamp": "2024-12-12T13:30:00Z",
    "impact": "high",
    "tags": ["usd"],
    "created_at": dt.datetime.utcnow().isoformat() + "Z",
}
score = dt.datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00")).timestamp()
r.zadd("news:events", {json.dumps(event): score})
```

### Consuming inside an analyzer
```python
import json, redis, datetime as dt
r = redis.Redis()
now = dt.datetime.utcnow().timestamp()
window = 30 * 60  # 30 minutes
items = r.zrangebyscore("news:events", now - window, now + window)
active = [json.loads(x) for x in items]
if active:
    reason = active[0]["title"]
    frame["features"]["news_active"] = True
    frame["features"]["news_reason"] = reason
```

## Operational considerations
- Ensure system clocks are synchronized; incorrect time can misalign buffer windows.
- External calendar APIs often have rate limits—cache responses when possible.
- If Redis is unavailable, analyzers should fail open with a warning rather than blocking all traffic.
- Monitor pruning jobs; an oversized set can degrade lookup performance.
- Consider storing only high‑impact events to reduce noise.
