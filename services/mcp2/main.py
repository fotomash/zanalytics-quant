import logging
import json
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


def load_session_manifest(path: str | Path = "session_manifest.yaml"):
    path = Path(path)
    try:
        with path.open("r", encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    except FileNotFoundError as exc:
        logger.error("session manifest not found at %s", path)
        raise
    except yaml.YAMLError as exc:
        logger.error("failed to parse session manifest %s: %s", path, exc)
        raise


def load_confidence_trace_matrix(path: str | Path = "confidence_trace_matrix.json"):
    path = Path(path)
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError as exc:
        logger.error("confidence trace matrix not found at %s", path)
        raise
    except json.JSONDecodeError as exc:
        logger.error("failed to parse confidence trace matrix %s: %s", path, exc)
        raise


def main() -> None:
    load_session_manifest()
    load_confidence_trace_matrix()


if __name__ == "__main__":
    main()
