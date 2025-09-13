# Whisperer Integration

The MCP2 service provides a `/llm/whisperer` endpoint for behavioral nudges and guidance.

## Basic Request

```bash
curl -sX POST http://localhost:8002/llm/whisperer \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Review my EURUSD risk"}'
```

Responses contain the model's suggestion and optional latency metrics.

## Configuration

- `MCP2_API_KEY` – required when auth is enabled
- `MCP_HOST` – base URL for remote Whisperer execution (see `whisperer_agent.py`)
- Prompts may be sourced from `session_manifest.yaml` or `docs/gpt_llm/whisperer_zanflow_pack/`

For more context on prompt packs and Redis caching, see `docs/gpt_llm/README.md`.
