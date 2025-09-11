Pulse Journal Envelopes (Active)
================================

Stable outer schema; payload evolves with `payload['v']`.

Schema (outer)
--------------

```
{
  "ts": float,           # epoch seconds
  "stream": str,         # "pulse.score" | "pulse.decision" | ...
  "symbol": str,         # e.g., "XAUUSD"
  "frame": str|null,     # e.g., "1m"
  "payload": { ... },    # versioned inner payload
  "trace_id": str|null,  # optional correlation id
  "host": str|null,      # optional hostname
  "build": str|null      # optional git sha/image tag
}
```

Example: score
--------------

```
{
  "ts": 1736370461.123,
  "stream": "pulse.score",
  "symbol": "XAUUSD",
  "frame": "1m",
  "payload": {"v": 1, "score": 0.74, "components": {"smc":0.4,"wyckoff":0.2,"session":0.14}, "weights": {"smc":0.5,"wyckoff":0.3,"session":0.2}},
  "trace_id": null
}
```

Contract policy
---------------

- Never break outer fields; add optional fields only
- Evolve `payload` under a version key (`v`), bumping as fields change
- Failing to publish must never impact trade flow (engine is fail‑closed)

