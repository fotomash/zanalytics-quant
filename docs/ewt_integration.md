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

This document outlines how Elliott Wave forecasting integrates with the enrichment pipeline.

## Components

- **Fractals** – detect significant pivot points to anchor wave counts.
- **Alligator** – three moving averages (jaw, teeth, lips) that help confirm trend direction.
- **Elliott Wave labelling** – marks impulsive and corrective waves for downstream analysis.
- **ML/LLM hooks** – optional machine‑learning ensemble or local LLM forecast extensions.

## Configuration

The module reads settings from `config/enrichment_ewt.yaml`:

```yaml
# config/enrichment_ewt.yaml
advanced:
  fractal_detector:
    enabled: true
    fractal_bars: 2
  elliott_wave:
    enabled: true
    min_pivot_distance: 5
    fib_retrace_threshold: 0.618
  alligator:
    enabled: true
    jaw: 13
    teeth: 8
    lips: 5
```

`ElliottConfig` in `utils/enrichment_config.py` exposes the following options:

- `enabled` – toggle Elliott Wave analysis.
- `ml_ensemble` – enable a machine-learning ensemble for scoring.
- `llm_max_tokens` – token limit for local LLM forecasts.

These settings may be defined in the enrichment configuration YAML or
programmatically via `EnrichmentConfig`.

## Local LLM Forecasts

`AdvancedProcessor` ships with a private `_llm_infer` helper that calls a
locally served model specified by the `LOCAL_LLM_MODEL` environment variable.
When configured, calls to `process` will populate an `ewt_forecast` field in the
result dictionary.

```
export LOCAL_LLM_MODEL=llama3:8b-instruct
```

The helper uses the `ollama` command line interface and respects
`llm_max_tokens` from the configuration.

## Reinforcement Learning Interface

For iterative experimentation a minimal `RLAgent` interface is provided.  The
agent defines `select_action`, `update` and `train` methods and can be supplied
to `AdvancedProcessor` for future reinforcement learning workflows.

```python
from utils.processors import AdvancedProcessor, RLAgent

agent = RLAgent()
processor = AdvancedProcessor(rl_agent=agent)
```

This interface is a placeholder and does not implement learning logic.

## Deployment

1. Copy `config/enrichment_ewt.yaml` to the target host.
2. Set the `ENRICHMENT_CONFIG` environment variable to point at the file.
3. Restart the enrichment service so the new modules and parameters are loaded.

## Testing

Unit coverage for the Elliott Wave tools can be exercised with pytest:

```bash
pytest -k ewt
```

Use sample OHLC data to validate fractal detection, wave labelling and Alligator alignment.

## Prometheus Metrics

The enrichment service exports counters and timers such as
`ewt_waves_detected_total` and `ewt_processing_seconds`. Ensure your
Prometheus scrape configuration targets the service and consider Grafana
dashboards to monitor forecast volume and processing latency.

