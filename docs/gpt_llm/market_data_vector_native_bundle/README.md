# Financial Market Data Vector-Native Bundle

## Overview

This bundle provides a vector-native, LLM-action-ready API for market summary, technical indicators, and asset correlation, with both YAML and JSON schemas, and a Python implementation.

## Files

- `openapi.yaml` — OpenAPI YAML schema for API/LLM Actions
- `action_contract.json` — JSON contract for OpenAI Custom GPT or similar
- `market_data_vector_native.py` — Python implementation (ready for FastAPI/Flask)
- `SCHEMA.md` — Human-readable schema
- `README.md` — This file

## Example Usage

```python
from market_data_vector_native import MarketDataVectorNative

mdn = MarketDataVectorNative()
result = mdn.create_summary()
print(result["summary"])
print(result["visualization"]["table_markdown"])
# To display the heatmap image, decode the base64 string and render as PNG
```

## API Integration

- Deploy the Python as a REST API (e.g., with FastAPI)
- Use the OpenAPI or JSON schema for LLM Actions or OpenAI Custom GPT
- Return both markdown tables and base64 images for inline display

## Vector-Native Features

- All time series and correlations are computed as vectors
- Output is suitable for embedding, clustering, and further vector-native analytics
