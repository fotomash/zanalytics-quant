#!/usr/bin/env python3
"""Verify that OpenAI action manifest names map to MCP server routes.

The script loads ``openai-actions.yaml`` at the project root and compares the
``name_for_model`` entries to the actual ``APIRoute`` values exposed by the
FastAPI app in ``backend/mcp/mcp_server.py``. Both HTTP method and path are
checked. If ``openapi.actions.yaml`` is present, its routes are also validated
to ensure they appear in the manifest. This helps catch stale manifest entries
and spec discrepancies.
"""
from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import urlparse
import types

import yaml
from fastapi.routing import APIRoute

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "openai-actions.yaml"
SPEC = ROOT / "openapi.actions.yaml"


def load_manifest() -> dict:
    """Load action definitions from ``openai-actions.yaml``."""
    with MANIFEST.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data or {}


def get_manifest_routes() -> dict[str, tuple[str, str]]:
    """Return mapping of action ``name_for_model`` -> (method, path)."""
    data = load_manifest()
    actions = data.get("actions", [])
    mapping: dict[str, tuple[str, str]] = {}
    for action in actions:
        name = action.get("name_for_model")
        url = action.get("action_url", "")
        method = action.get("method", "GET").upper()
        path = urlparse(url).path
        if name:
            mapping[name] = (method, path)
    return mapping


def get_server_routes() -> set[tuple[str, str]]:
    """Return set of (method, path) pairs served by the MCP FastAPI app."""
    sys.path.insert(0, str(ROOT))
    sys.modules.setdefault("mt5_adapter", types.SimpleNamespace(init_mt5=lambda: None))
    try:
        from backend.mcp.mcp_server import app  # type: ignore
    except Exception as exc:  # pragma: no cover - import failure reported
        print(f"Failed to import mcp_server: {exc}")
        return set()

    return {
        (method, route.path)
        for route in app.routes
        if isinstance(route, APIRoute)
        for method in route.methods or set()
    }


def get_spec_routes() -> set[tuple[str, str]]:
    """Return set of (method, path) pairs defined in ``openapi.actions.yaml``."""
    if not SPEC.exists():
        return set()

    with SPEC.open("r", encoding="utf-8") as f:
        spec = yaml.safe_load(f) or {}

    routes: set[tuple[str, str]] = set()
    for path, methods in (spec.get("paths") or {}).items():
        for method, _details in methods.items():
            if method.startswith("x-"):
                continue
            routes.add((method.upper(), path))
    return routes


def main() -> int:
    manifest = get_manifest_routes()
    server_routes = get_server_routes()
    spec_routes = get_spec_routes()

    manifest_routes = {(method, path) for method, path in manifest.values()}
    missing = {
        name: (method, path)
        for name, (method, path) in manifest.items()
        if (method, path) not in server_routes
    }

    status = 0
    if missing:
        print("Missing routes for actions:")
        for name, (method, path) in sorted(missing.items()):
            print(f"  {name}: {method} {path}")
        status = 1
    else:
        print("All manifest actions have matching server routes.")

    if spec_routes:
        missing_manifest = spec_routes - manifest_routes
        if missing_manifest:
            print("Missing manifest entries for spec routes:")
            for method, path in sorted(missing_manifest):
                print(f"  {method} {path}")
            status = 1
        else:
            print("All spec routes are present in the manifest.")

    return status


if __name__ == "__main__":
    raise SystemExit(main())
