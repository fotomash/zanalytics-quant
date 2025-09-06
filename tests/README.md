# Tests

## Smoke tests

Run the smoke suite from the repository root to quickly verify that the Pulse kernel loads and can process a simple frame:

```bash
pytest -k "pulse_api_smoke"
```

These tests instantiate `PulseKernel` with `pulse_config.yaml`, check that the kernel reports a `behavioral_state`, and ensure that calling `on_frame` returns an `action`.

## Adding tests

Place new tests in this `tests/` directory and name files and functions with the `test_` prefix so that pytest can discover them. Existing smoke tests live in `test_pulse_api_smoke.py`; create additional modules or extend this file to cover new components.
