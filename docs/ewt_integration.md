# EWT Integration

This document outlines how Elliott Wave forecasting integrates with the enrichment pipeline.

## Configuration

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

