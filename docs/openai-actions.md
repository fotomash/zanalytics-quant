# OpenAI Actions

This project exposes a set of OpenAI Actions defined in `openai-actions.yaml`.
The manifest lists each action name, URL and parameter schema. Two helper
scripts ensure the manifest stays in sync with the MCP server and that endpoints
respond as expected. See [scripts/verify_actions.py](../scripts/verify_actions.py)
and [scripts/test_actions.py](../scripts/test_actions.py) for simple tooling.

## Endpoints

### `POST /api/v1/actions/query`
Execute an action via the Actions Bus.

**Sample request**

```json
{
  "type": "session_boot",
  "payload": { "user_id": "demo" }
}
```

### `GET /api/v1/actions/query`
Fetch read-only data using query parameters.

**Sample request**

```json
{
  "type": "trades_recent",
  "limit": 5
}
```

### `GET /api/v1/actions/read`
Alias of the query endpoint for read-only environments.

**Sample request**

```json
{
  "type": "account_info"
}
```

## Supported action types

Common verbs include:

- `session_boot`
- `trades_recent`
- `account_info`

## Verify action coverage

Run the verification script to confirm that every `name_for_model` entry in the
manifest has a corresponding route implemented by the MCP FastAPI server:

```bash
python scripts/verify_actions.py
```

Any missing routes are printed to STDOUT and the script exits with a non-zero
status.

## Smoke-test action endpoints

`scripts/test_actions.py` performs a minimal HTTP request against each action.
It uses placeholder values for required parameters and reports whether the
endpoint returned a non-error status code.

```bash
python scripts/test_actions.py
```

These checks are lightweight and intended for developer workflows. They do not
replace comprehensive testing of the underlying services.
