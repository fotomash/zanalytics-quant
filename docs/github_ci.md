# GitHub CI Workflow

The repository uses two primary GitHub Actions workflows to validate changes and gate releases for v2.1beta.

## Workflows
- **CI (`ci.yml`)** – runs on every push or pull request. It installs dependencies, lints Dockerfiles and docstrings, validates action routes, and executes `pytest -m "not mt5"`.
- **Pulse Integration Tests (`pulse_tests.yml`)** – triggered when Pulse or risk modules change. It sets up Python, installs dependencies with coverage tools, runs `tests/test_pulse_integration.py` with coverage, and uploads the report to Codecov.

## Coverage thresholds
Releases target a minimum **85% line coverage** from the Pulse integration suite. Failing to meet the threshold blocks the release.

## Release gating for v2.1beta
A v2.1beta release requires:
1. Both workflows passing.
2. Coverage meeting the 85% minimum.
3. Manual approval before tagging.

These safeguards ensure that only well-tested, instrumented code reaches the v2.1beta line.
