# Running Tests

To execute the automated Django test suite:

```bash
pip install -r requirements.txt
export DJANGO_SECRET_KEY=test-secret
pytest
```

Tests run against the lightweight SQLite database defined in `backend/django/app/test_settings.py`.

## Analyzer Tests

The confluence analyzers combine Wyckoff pattern detection and Smart Money Concepts features. After installing dependencies with `pip install -r requirements.txt`, run the dedicated tests:

```bash
pytest tests/test_analyzers.py
```
