# OpenAI Actions

This project exposes a set of OpenAI Actions defined in `openai-actions.yaml`.
The manifest lists each action name, URL and parameter schema. Two helper
scripts ensure the manifest stays in sync with the MCP server and that endpoints
respond as expected.

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
