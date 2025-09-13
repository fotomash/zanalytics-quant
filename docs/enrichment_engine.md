# Enrichment Engine

The enrichment engine augments raw market data with derived signals and metadata.
It consumes tick and bar streams, runs them through a configurable processor
pipeline, and publishes enriched events for downstream services. The reference
implementation in `utils/enrich.py` currently adds only four attributes:
Wyckoff phase detection, an aggregated confidence score, a human-readable nudge
string, and an embedding vector.

## Architecture

The engine is composed of an input adapter, a processor pipeline, and output
sinks. Each processor is a small unit of enrichment logic that transforms the
incoming `DataFrame` and forwards it to the next stage. Processors are loaded at
runtime based on a YAML or JSON configuration file.

## Configuration

Configuration defines which processors run and in what order.  The default
grouped configuration lives in
[`config/enrichment_default.yaml`](../config/enrichment_default.yaml) and is
split into four hierarchies: **core**, **technical**, **structure**, and
**advanced**.  Each group toggles a set of enrichment modules:

```yaml
core:
  structure_validator: true

technical:
  groups:
    trend:
      enabled: true
      indicators:
        sma: true
        ema: false
    oscillators:
      enabled: true
      indicators:
        rsi: true
        macd: true

structure:
  smc: true
  wyckoff: true

advanced:
  liquidity_engine: true
  context_analyzer: true
  fvg_locator: true
  predictive_scorer: true
```

For harmonic pattern detection with vector database persistence, a dedicated
configuration is provided at
[`config/enrichment_harmonic.yaml`](../config/enrichment_harmonic.yaml).  It
defines the harmonic tolerance and pivot window along with the target
embedding model and collection name.

For vectorized runs, [`config/enrichment_vectorized.yaml`](../config/enrichment_vectorized.yaml)
defines nested flags for individual features:

```yaml
smc:
  liquidity_grabs: true
  order_blocks: true
poi:
  imbalances: true
rsi:
  overbought_threshold: 70
```

### Pydantic configuration model

The groups are represented by the Pydantic
`EnrichmentConfig` model.  It can be loaded from YAML and converted into the
module map expected by the engine:

```python
from utils.enrichment_config import EnrichmentConfig, load_enrichment_config

# Load defaults from config/enrichment_default.yaml
cfg: EnrichmentConfig = load_enrichment_config()
cfg.technical.groups["trend"].indicators["ema"] = True  # enable EMA on the fly

# Translate grouped toggles into per-module configs
module_cfg = cfg.to_module_configs()

# Load harmonic-focused configuration
harmonic_cfg = load_enrichment_config("config/enrichment_harmonic.yaml")
```

### Dynamic configuration API

Processors can be reconfigured without a restart by posting the generated module
config to the API:

```python
import requests

requests.post("https://engine.example/api/config", json=module_cfg, timeout=10)
```

### Selective enrichment and metadata decoupling

Each group or indicator can be toggled independently so only the desired
enrichment steps run.  The engine publishes the enriched payload separately from
its metadata, allowing consumers to fetch lightweight context only when needed.

### Serialization options

Published payloads use MessagePack when the optional ``msgpack`` dependency is
available and fall back to JSON otherwise, keeping wire formats compact while
remaining universally compatible.

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

## Future Work

Full technical indicator libraries and options Greek calculations remain out of
scope for the core engine and are planned for later phases.
