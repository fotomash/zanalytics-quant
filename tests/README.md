# Tests

## Smoke tests

Run the smoke suite from the repository root to quickly verify that the Pulse kernel loads and can process a simple frame:

```bash
pytest -k "pulse_api_smoke"
```

These tests instantiate `PulseKernel` with `pulse_config.yaml`, check that the kernel reports a `behavioral_state`, and ensure that calling `on_frame` returns an `action`.

## Adding tests

Place new tests in this `tests/` directory and name files and functions with the `test_` prefix so that pytest can discover them. Existing smoke tests live in `test_pulse_api_smoke.py`; create additional modules or extend this file to cover new components.

## MCP v2 API tests

`tests/test_mcp2.py` exercises the `services/mcp2` FastAPI server. The module provides an `app_client` fixture that patches Redis and Postgres with in-memory `AsyncMock` stubs so tests can assert cache hits and database fallbacks without external services. Reuse this fixture when extending MCP v2 coverage.

## Redis caching tests

New tests verify that Redis is used as a caching layer and fallback for Streamlit helpers. Run them directly or as part of the full suite:

```bash
pytest tests/test_caching_service.py tests/test_streamlit_api_cache.py
```
