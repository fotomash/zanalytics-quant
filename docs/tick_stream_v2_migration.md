# Tick Stream v2 Migration

Redis tick streams now include a version prefix. Consumers must read from keys like `v2:ticks:*` instead of `ticks:*`.

## Default Prefix
- `STREAM_VERSION_PREFIX` (env var) controls the prefix; default is `v2`.
- Services such as ingest, enrich, and tick-to-bar publish to `v2:ticks:<symbol>`.

## Action Required
Update any custom consumers to subscribe to `v2:ticks:<symbol>` or set `STREAM_VERSION_PREFIX` to match your deployment.
