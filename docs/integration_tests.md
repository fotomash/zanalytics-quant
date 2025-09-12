# Integration Tests

## Scope
The integration test suite verifies the bootstrap helpers in `integration.bootstrap_os_integration`.
It ensures that:
- `initialize_risk_enforcer` returns a singleton with a `check_trade` hook.
- `initialize_ml_bridge` uses any provided Redis client.
- `bootstrap_all` returns both instances and reuses the previously created bridge.

## Running the tests
Install dependencies and execute the integration tests:

```bash
pip install -r requirements.txt -c constraints.txt
pytest integration/tests/test_bootstrap_os_integration.py -q
```

## Expected output
All three tests should pass, for example:

```
3 passed in 0.XXs
```

Passing confirms the risk enforcer is instantiated once, the ML bridge respects the supplied Redis client, and the combined bootstrap exposes both objects.
