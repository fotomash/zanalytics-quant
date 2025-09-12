# Tick Stream v2 Migration

Redis tick streams now include a version prefix. Consumers must read from keys like `v2:ticks:*` instead of `ticks:*`.

## Default Prefix
- `STREAM_VERSION_PREFIX` (env var) controls the prefix; default is `v2`.

## Services Using the Prefix
The following services publish to or consume from the versioned tick streams:

- **Ingest service** – collects raw ticks and writes them to `v2:ticks:l1`. See `services/ingest/ingest_service.py`.
- **Enrichment service** – reads from `v2:ticks:l1` and stores enriched ticks. See `services/enrichment/main.py`.
- **Tick-to-bar aggregator** – consumes `v2:ticks:<symbol>` and emits OHLC bars. See `services/tick_to_bar.py`.

## Action Required
Update any custom consumers to subscribe to `v2:ticks:<symbol>` or set `STREAM_VERSION_PREFIX` to match your deployment.
