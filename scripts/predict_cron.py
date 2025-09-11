"""Run prediction cron with configurable risk threshold.

The script reads the risk threshold from the ``RISK_THRESHOLD``
environment variable or from ``config/predict_cron.yaml``.
It also provides a helper to compute a recommended threshold from
historical silence/spike data.
"""

from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path
from statistics import mean, stdev
from typing import List, Optional

import yaml

# Default config path can be overridden for tests or alternate deployments
CONFIG_PATH = Path(os.getenv("PREDICT_CRON_CONFIG", "config/predict_cron.yaml"))


def _load_config_threshold() -> Optional[float]:
    """Load threshold from the YAML config file if available."""
    if CONFIG_PATH.exists():
        with CONFIG_PATH.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
            value = data.get("risk_threshold")
            if value is not None:
                try:
                    return float(value)
                except (TypeError, ValueError):
                    pass
    return None


def get_risk_threshold() -> float:
    """Return risk threshold from env var or config, defaulting to 0.5."""
    env_val = os.getenv("RISK_THRESHOLD")
    if env_val is not None:
        try:
            return float(env_val)
        except ValueError:
            pass
    config_val = _load_config_threshold()
    if config_val is not None:
        return config_val
    return 0.5


def recommend_threshold(history_path: str) -> float:
    """Compute a recommended threshold from historical data.

    The history file must be a CSV with a ``spike`` column containing
    numeric magnitudes. The recommended threshold is ``mean + 2*stdev``
    of these spike values.
    """
    values: List[float] = []
    with open(history_path, newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            try:
                values.append(float(row["spike"]))
            except (KeyError, ValueError):
                # Ignore rows missing or with invalid spike values
                continue
    if not values:
        raise ValueError("no spike data found in history file")
    avg = mean(values)
    sd = stdev(values) if len(values) > 1 else 0.0
    return avg + 2 * sd


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Prediction cron")
    parser.add_argument(
        "--history",
        help="CSV file with past silence/spike data to compute a recommended threshold",
    )
    args = parser.parse_args(argv)

    threshold = get_risk_threshold()
    print(f"Using risk threshold: {threshold}")

    if args.history:
        try:
            recommended = recommend_threshold(args.history)
            print(f"Recommended threshold based on history: {recommended}")
        except Exception as exc:
            print(f"Unable to compute recommended threshold: {exc}")


if __name__ == "__main__":  # pragma: no cover - manual execution
    main()
