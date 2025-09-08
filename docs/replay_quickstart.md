Replay Quickstart (Experimental)
================================

Reproduce a trading hour locally from journal topics and bar streams.

Prereqs
-------

- Redpanda up: `docker compose -f docker-compose.yml -f docker-compose.kafka.yml up -d`
- Journal enabled in staging (collect a sample)

Steps
-----

1) Export one hour of `pulse.journal` (staging)

```
rpk topic consume pulse.journal --brokers=localhost:29092 -n 10000 --format '{{.Value}}' > /tmp/journal.jsonl
```

2) Filter events for a symbol/time window

```
grep '"symbol":"XAUUSD"' /tmp/journal.jsonl | sed -n '1,2000p' > /tmp/journal.xau.jsonl
```

3) Recalculate scores offline (not provided here) or visualize decision envelopes

- Use a small Python script to parse JSONL and summarize.

Notes
-----

- This doc will evolve with replay tooling; for now it demonstrates topic export and filtering.

