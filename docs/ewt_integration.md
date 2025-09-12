# EWT Integration

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

