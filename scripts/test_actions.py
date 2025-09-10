#!/usr/bin/env python3
"""Send minimal requests to each OpenAI action endpoint.

Reads action definitions from ``openai-actions.yaml`` and performs a simple
HTTP request for each one, using placeholder values for required parameters.
The script prints a short summary showing which actions responded without
errors. It is a lightweight smoke test and does not validate response content.
"""
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

import httpx
import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "openai-actions.yaml"


def load_actions() -> list[dict]:
    with MANIFEST.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("actions", [])


def sample_value(field: dict):
    if isinstance(field, dict):
        if "enum" in field:
            return field["enum"][0]
        t = field.get("type")
        if t == "string":
            return ""
        if t in {"integer", "number"}:
            return 0
        if t == "boolean":
            return False
    return None


def build_payload(schema: dict) -> dict:
    payload: dict = {}
    props = schema.get("properties", {})
    required = schema.get("required", [])
    for name in required:
        payload[name] = sample_value(props.get(name, {}))
    return payload


def main() -> int:
    actions = load_actions()
    with httpx.Client(timeout=5) as client:
        for action in actions:
            name = action.get("name_for_model")
            url = action.get("action_url")
            method = action.get("method", "GET").upper()
            params_schema = action.get("parameters", {})
            payload = build_payload(params_schema)

            # Replace path parameters in URL
            if url:
                for match in re.findall(r"{(.*?)}", url):
                    replacement = payload.get(match, 1)
                    url = url.replace(f"{{{match}}}", str(replacement))
            else:
                print(f"{name}: missing URL")
                continue

            try:
                if method == "GET":
                    resp = client.get(url, params=payload)
                else:
                    resp = client.request(method, url, json=payload)
                status = resp.status_code
                ok = 200 <= status < 400
                print(f"{name}: {'OK' if ok else f'HTTP {status}'}")
            except Exception as exc:  # pragma: no cover - network errors
                print(f"{name}: error {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
