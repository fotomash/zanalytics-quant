import csv
import logging
from pathlib import Path
from typing import Dict, Tuple, List

import yaml

from services.mcp2.vector.embeddings import embed

logger = logging.getLogger(__name__)


def _load_field_patch() -> Dict[str, object]:
    """Load normalization rules and field mappings from YAML patch."""
    default_patch = {
        "normalization": {
            "lowercase": True,
            "strip": True,
            "replace": {" ": "_", "-": "_"},
        },
        "field_mappings": {"volume": ["volume"], "tick_volume": ["tick_volume"]},
    }
    patch_path = Path(__file__).resolve().parent / "volume_field_clarity_patch.yaml"
    try:
        with patch_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            patch = {
                "normalization": data.get("normalization", default_patch["normalization"]),
                "field_mappings": data.get("field_mappings", default_patch["field_mappings"]),
            }
            logger.info("loaded volume field patch", extra={"patch": patch})
            return patch
    except FileNotFoundError:
        logger.warning(
            "volume_field_clarity_patch.yaml not found; using defaults",
            extra={"defaults": default_patch},
        )
    except Exception:
        logger.exception("failed to load volume field patch")
    return default_patch


FIELD_PATCH = _load_field_patch()


def _normalize_key(key: str) -> str:
    norm = key
    opts = FIELD_PATCH.get("normalization", {})
    if opts.get("lowercase"):
        norm = norm.lower()
    if opts.get("strip"):
        norm = norm.strip()
    for old, new in opts.get("replace", {}).items():
        norm = norm.replace(old, new)
    return norm


def _build_alias_map() -> Dict[str, str]:
    alias_map: Dict[str, str] = {}
    for canonical, aliases in FIELD_PATCH.get("field_mappings", {}).items():
        for alias in aliases:
            alias_map[_normalize_key(alias)] = canonical
    return alias_map


ALIAS_TO_CANONICAL = _build_alias_map()
REQUIRED_VOLUME_FIELDS = list(FIELD_PATCH.get("field_mappings", {}).keys())


def _apply_field_mappings(payload: Dict) -> Dict:
    mapped: Dict[str, object] = {}
    for key, value in payload.items():
        canonical = ALIAS_TO_CANONICAL.get(_normalize_key(key), _normalize_key(key))
        mapped[canonical] = value
    return mapped


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

        payload = _apply_field_mappings(payload)

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

        volume_candidates = [f for f in REQUIRED_VOLUME_FIELDS if f in payload]
        if not volume_candidates:
            logger.warning(
                "missing volume field",
                extra={"required": REQUIRED_VOLUME_FIELDS},
            )
        elif len(volume_candidates) > 1:
            logger.warning(
                "ambiguous volume fields",
                extra={"fields": volume_candidates},
            )
        if volume_candidates:
            metadata["volume"] = payload[volume_candidates[0]]

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
