"""Validate required modules import before starting service."""

import importlib
import sys

REQUIRED_MODULES = [
    "confluent_kafka",
    "requests",
    "services.vectorization_service.brown_vector_store_integration",
    "services.vectorization_service.pipeline",
]


def main() -> None:
    missing: list[str] = []
    for module in REQUIRED_MODULES:
        try:
            importlib.import_module(module)
        except Exception as exc:  # pragma: no cover - defensive
            missing.append(f"{module}: {exc}")
    if missing:
        for msg in missing:
            print(f"Failed to import {msg}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
