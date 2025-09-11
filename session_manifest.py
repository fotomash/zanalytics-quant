from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

import yaml


DEFAULT_MANIFEST = os.getenv("SESSION_MANIFEST", "configs/session_manifest.yaml")


class ManifestNotFound(Exception):
    pass


@lru_cache(maxsize=1)
def _load(path: str = DEFAULT_MANIFEST) -> dict[str, Any]:
    if not os.path.exists(path):
        raise ManifestNotFound(f"session manifest not found: {path}")
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return data


def load_prompt(key: str, *, path: str = DEFAULT_MANIFEST) -> str:
    data = _load(path)
    prompts = (data or {}).get("llm_prompts", {})
    if key not in prompts:
        raise KeyError(f"prompt key not found: {key}")
    return str(prompts[key])


__all__ = ["load_prompt", "ManifestNotFound"]

