#!/usr/bin/env python3
"""Verify that OpenAI action manifest names map to MCP server routes.

The script loads ``openai-actions.yaml`` at the project root and compares the
``name_for_model`` entries to the actual ``APIRoute.path`` values exposed by the
FastAPI app in ``backend/mcp/mcp_server.py``. It helps catch stale manifest
entries that no longer have a corresponding server implementation.
"""
from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import urlparse

import yaml
from fastapi.routing import APIRoute

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "openai-actions.yaml"


def load_manifest() -> dict:
    """Load action definitions from ``openai-actions.yaml``."""
    with MANIFEST.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data or {}


def get_manifest_paths() -> dict[str, str]:
    """Return mapping of action ``name_for_model`` -> path."""
    data = load_manifest()
    actions = data.get("actions", [])
    mapping: dict[str, str] = {}
    for action in actions:
        name = action.get("name_for_model")
        url = action.get("action_url", "")
        path = urlparse(url).path
        if name:
            mapping[name] = path
    return mapping


def get_server_paths() -> set[str]:
    """Return set of paths served by the MCP FastAPI app."""
    sys.path.insert(0, str(ROOT / "backend" / "mcp"))
    try:
        from mcp_server import app  # type: ignore
    except Exception as exc:  # pragma: no cover - import failure reported
        print(f"Failed to import mcp_server: {exc}")
        return set()

    return {
        route.path
        for route in app.routes
        if isinstance(route, APIRoute)
    }


def main() -> int:
    manifest = get_manifest_paths()
    server_paths = get_server_paths()

    missing = {name: path for name, path in manifest.items() if path not in server_paths}

    if missing:
        print("Missing routes for actions:")
        for name, path in sorted(missing.items()):
            print(f"  {name}: {path}")
        return 1

    print("All manifest actions have matching server routes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
