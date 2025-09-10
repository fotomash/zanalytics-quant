#!/usr/bin/env python3
"""Validate OPENAI_ACTIONS.yaml endpoints against FastAPI and Django routes."""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Iterable, Set

import yaml

ROOT = Path(__file__).resolve().parents[1]


def normalize(path: str) -> str:
    """Normalize path to have leading slash and no trailing slash."""
    if not path.startswith('/'):
        path = '/' + path
    if len(path) > 1:
        path = path.rstrip('/')
    return path


def load_actions(path: Path) -> Set[str]:
    data = yaml.safe_load(path.read_text())
    endpoints: Set[str] = set()
    for action in data.get('actions', []):
        endpoint = action.get('endpoint')
        if endpoint:
            endpoints.add(normalize(endpoint))
    return endpoints


def get_fastapi_routes() -> Set[str]:
    sys.path.insert(0, str(ROOT / 'backend' / 'mcp'))
    try:
        from mcp_server import app  # type: ignore
    except Exception:
        return set()

    routes = set()
    for route in getattr(app, 'routes', []):
        path = getattr(route, 'path', None)
        if path:
            routes.add(normalize(path))
    return routes


def _normalize_django_pattern(pattern: str) -> str:
    pattern = re.sub(r"<[^:>]+:([^>]+)>", r"{\1}", pattern)
    pattern = re.sub(r"<([^>]+)>", r"{\1}", pattern)
    pattern = pattern.lstrip("^").rstrip("$")
    return normalize(pattern)



def get_django_routes() -> Set[str]:
    sys.path.insert(0, str(ROOT / 'backend' / 'django'))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
    os.environ.setdefault('DJANGO_SECRET_KEY', 'dummy')
    try:
        import django
        django.setup()
        from django.urls import get_resolver, URLPattern, URLResolver  # type: ignore
    except Exception:
        return set()

    resolver = get_resolver()
    found: Set[str] = set()

    def walk(patterns: Iterable, prefix: str = ''):
        for p in patterns:
            segment = getattr(p.pattern, '_route', getattr(p.pattern, 'pattern', ''))
            if isinstance(p, URLResolver):
                walk(p.url_patterns, prefix + segment)
            elif isinstance(p, URLPattern):
                found.add(_normalize_django_pattern(prefix + segment))
    walk(resolver.url_patterns)
    return found


def main() -> int:
    actions_path = ROOT / 'actions' / 'OPENAI_ACTIONS.yaml'
    action_endpoints = load_actions(actions_path)

    fastapi_routes = get_fastapi_routes()
    django_routes = get_django_routes()
    available = fastapi_routes.union(django_routes)

    missing = sorted(ep for ep in action_endpoints if ep not in available)
    if missing:
        print('Missing endpoints:', '\n - '.join(missing))
        return 1

    print('All action endpoints have matching routes.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
