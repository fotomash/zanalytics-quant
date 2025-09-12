# Operations Guide

## Metrics Endpoints

The system exposes Prometheus metrics at the `/metrics` HTTP endpoint.
Two processor focused metrics are published:

- `processor_process_time_seconds` – summary of time spent in processor functions.
- `processor_error_count` – counter of processor errors.

These metrics can be scraped by a Prometheus server for monitoring and alerting.

## Error Handling Strategy

Processors guard against empty or low-volume tick frames. Each processor
returns immediately when provided an empty `DataFrame` (`if df.empty: return`)
and any exceptions encountered during processing increment the
`processor_error_count` metric before being re-raised.

## Related Documentation

For architecture and deployment details, see [Enrichment Engine](enrichment_engine.md).
