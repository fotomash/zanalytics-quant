from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import yaml


def build_session_manifest(
    responses: Dict[str, Any],
    design_path: Path | str = Path("session_manager_design.yaml"),
) -> Dict[str, Any]:
    """Map user responses to the session manifest schema.

    Parameters
    ----------
    responses:
        Dictionary containing values collected from the user.
    design_path:
        Location of the design YAML describing the manifest structure.

    Returns
    -------
    dict
        Completed session manifest with defaults and metadata applied.
    """
    path = Path(design_path)
    design = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
    manifest: Dict[str, Any] = deepcopy(design)

    for key, value in responses.items():
        if value is not None:
            manifest[key] = value

    metadata = manifest.setdefault("metadata", {})
    if not metadata.get("created_at"):
        metadata["created_at"] = datetime.utcnow().isoformat()

    return manifest
