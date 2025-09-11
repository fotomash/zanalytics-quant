import csv
import logging
from pathlib import Path
from typing import Dict, Tuple, List

import yaml

from services.mcp2.vector.embeddings import embed

logger = logging.getLogger(__name__)


def _load_volume_fields() -> List[str]:
    """Load volume field names from volume_field_clarity_patch.yaml if available."""
    default_fields = ["volume", "tick_volume", "inferred_volume", "true_volume"]
    patch_path = Path(__file__).resolve().parents[2] / "volume_field_clarity_patch.yaml"
    try:
        with patch_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            fields = (
                data.get("volume_fields")
                or data.get("fields")
                or data.get("volume")
            )
            if isinstance(fields, list) and fields:
                logger.info(
                    "loaded volume field patch", extra={"fields": fields}
                )
                return fields
            logger.warning(
                "volume_field_clarity_patch.yaml missing expected keys; using defaults",
                extra={"defaults": default_fields},
            )
    except FileNotFoundError:
        logger.warning(
            "volume_field_clarity_patch.yaml not found; using defaults",
            extra={"defaults": default_fields},
        )
    except Exception:
        logger.exception("failed to load volume field patch")
    return default_fields


VOLUME_FIELDS = _load_volume_fields()


def vectorize_payload(payload: Dict) -> Tuple[List[float], Dict]:
    """Return embedding and metadata for a CSV payload.

    Parameters
    ----------
    payload: dict
        Row data from CSV or any mapping of field names to values.

    Returns
    -------
    Tuple[List[float], Dict]
        A tuple containing the embedding list and associated metadata.
    """
    try:
        if not isinstance(payload, dict):
            raise TypeError("payload must be a dict")

        text_parts = []
        for key in sorted(payload.keys()):
            value = payload.get(key)
            if value is None:
                continue
            text_parts.append(str(value))
        text = " ".join(text_parts)

        embedding = embed(text)

        metadata: Dict[str, object] = {}
        for field in ["timestamp", "symbol", "open", "high", "low", "close"]:
            if field in payload:
                metadata[field] = payload[field]

        for vol_field in VOLUME_FIELDS:
            if vol_field in payload:
                metadata["volume"] = payload[vol_field]
                break

        return embedding, metadata
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception(
            "vectorize_payload failed",
            extra={"payload_preview": {k: payload.get(k) for k in list(payload)[:5]}},
        )
        return [], {"error": str(exc)}


def vectorize_csv(path: str) -> List[Tuple[List[float], Dict]]:
    """Vectorize each row of a CSV file."""
    results: List[Tuple[List[float], Dict]] = []
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                results.append(vectorize_payload(row))
    except FileNotFoundError:
        logger.error("csv file not found", extra={"path": path})
    except Exception:
        logger.exception("failed to vectorize csv", extra={"path": path})
    return results


if __name__ == "__main__":  # pragma: no cover
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Vectorize CSV records")
    parser.add_argument("path", help="Path to CSV file")
    args = parser.parse_args()

    vectors = vectorize_csv(args.path)
    print(json.dumps(vectors, default=str))
