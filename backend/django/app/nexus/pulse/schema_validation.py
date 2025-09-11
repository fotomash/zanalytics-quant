from __future__ import annotations

"""
Optional JSON Schema validators for Pulse payloads.

If fastjsonschema or schema files are unavailable, validators no-op.
"""

from pathlib import Path
from typing import Any, Callable, Optional, Tuple

Validator = Callable[[Any], Any]

_validate_status: Optional[Validator] = None
_validate_detail: Optional[Validator] = None


def _compile(name: str) -> Optional[Validator]:
    try:
        import json
        import fastjsonschema  # type: ignore

        here = Path(__file__).resolve()
        repo_root = here.parents[6] if len(here.parents) >= 7 else here.parents[0]
        schema_path = repo_root / "_schema" / name
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        return fastjsonschema.compile(schema)
    except Exception:
        return None


def _ensure_compiled() -> None:
    global _validate_status, _validate_detail
    if _validate_status is None:
        _validate_status = _compile("pulse.status.schema.json")
    if _validate_detail is None:
        _validate_detail = _compile("pulse.detail.schema.json")


def validate_pulse_status(payload: Any) -> Tuple[bool, Optional[str]]:
    """Validate status payload against JSON Schema if available."""
    _ensure_compiled()
    if _validate_status is None:
        return True, None
    try:
        _validate_status(payload)
        return True, None
    except Exception as e:  # fastjsonschema.JsonSchemaException
        return False, str(e)


def validate_pulse_detail(payload: Any) -> Tuple[bool, Optional[str]]:
    """Validate detail payload against JSON Schema if available."""
    _ensure_compiled()
    if _validate_detail is None:
        return True, None
    try:
        _validate_detail(payload)
        return True, None
    except Exception as e:
        return False, str(e)


__all__ = ["validate_pulse_status", "validate_pulse_detail"]

