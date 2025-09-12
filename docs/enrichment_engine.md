# Enrichment Engine

The enrichment engine augments raw market data with derived signals and metadata.
It consumes tick and bar streams, runs them through a configurable processor
pipeline, and publishes enriched events for downstream services. The reference
implementation in `utils/enrich.py` currently adds only four attributes:
Wyckoff phase detection, an aggregated confidence score, a human-readable
nudge, and an embedding vector. Technical indicators and options Greeks are
not part of the core engine and are tracked as future work.

## Architecture

The engine is composed of an input adapter, a processor pipeline, and output
sinks. Each processor is a small unit of enrichment logic that transforms the
incoming `DataFrame` and forwards it to the next stage. Processors are loaded at
runtime based on a YAML or JSON configuration file.

## Configuration

Configuration defines which processors run and in what order. A minimal YAML
configuration looks like:

```yaml
pipeline:
  processors:
    - name: enrich_prices
      class: EnrichPriceProcessor
      params:
        source: prices
    - name: add_sentiment
      class: SentimentProcessor
```

The equivalent JSON configuration:

```json
{
  "pipeline": {
    "processors": [
      {"name": "enrich_prices", "class": "EnrichPriceProcessor", "params": {"source": "prices"}},
      {"name": "add_sentiment", "class": "SentimentProcessor"}
    ]
  }
}
```

## Dynamic configuration API

Processors can be reconfigured without a restart by calling the configuration
endpoint:

```python
import requests

config = {"processors": [{"name": "add_sentiment", "enabled": True}]}
requests.post("https://engine.example/api/config", json=config, timeout=10)
```

## Processors

Processors are pluggable classes that implement a `process(df)` method. Typical
processors add derived metrics, filter noisy data, or join external datasets.
Custom processors can be registered by placing them on the Python path and
referencing them in the configuration.

## Deployment

The engine runs as a Docker service. Provide the configuration file through a
volume mount or remote URL and set the `ENRICHMENT_CONFIG` environment variable
accordingly. Updates to the configuration endpoint allow on-the-fly tuning
without redeployment.

For operational metrics and monitoring details see the
[Operations Guide](operations.md).
