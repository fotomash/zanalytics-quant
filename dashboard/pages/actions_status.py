"""Streamlit page to inspect and ping registered actions.

The page loads action metadata from ``docs/actions-tracker.md`` or
``actions/OPENAI_ACTIONS.yaml`` and renders an interactive panel for
basic diagnostics.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable

import requests
import streamlit as st
import yaml

# Root of the repository to resolve data files regardless of CWD
_REPO_ROOT = Path(__file__).resolve().parents[2]


@st.cache_data(ttl=900)
def load_actions() -> Iterable[Dict[str, Any]]:
    """Return available actions with minimal metadata.

    The loader first attempts to parse ``actions/OPENAI_ACTIONS.yaml``. If the
    YAML file is missing or malformed, it falls back to parsing the first table
    in ``docs/actions-tracker.md``.
    """

    yaml_path = _REPO_ROOT / "actions" / "OPENAI_ACTIONS.yaml"
    if yaml_path.exists():
        try:
            data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
            return data.get("actions", [])
        except yaml.YAMLError:
            pass

    md_path = _REPO_ROOT / "docs" / "actions-tracker.md"
    actions = []
    if md_path.exists():
        lines = md_path.read_text(encoding="utf-8").splitlines()
        table = False
        for line in lines:
            if line.startswith("| Source"):
                table = True
                continue
            if table:
                if not line.strip().startswith("|"):
                    break
                cells = [c.strip() for c in line.split("|")[1:-1]]
                if len(cells) >= 5:
                    actions.append(
                        {
                            "source": cells[0],
                            "name": cells[1],
                            "endpoint": cells[2],
                            "method": cells[3],
                            "description": cells[4],
                        }
                    )
    return actions


def ping_action(base_url: str, action: Dict[str, Any]) -> Dict[str, Any]:
    """Invoke ``action`` at ``base_url`` and return its JSON response."""

    url = f"{base_url}{action.get('endpoint', '')}"
    method = action.get("method", "GET").upper()
    try:
        resp = requests.request(method, url, timeout=5)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:  # Broad catch to surface errors in UI
        return {"error": str(exc)}


def main() -> None:
    st.set_page_config(page_title="Actions", page_icon="🛠", layout="wide")
    st.title("Actions Status")

    base_url = os.getenv("ACTIONS_BASE_URL", "http://localhost:8000")

    for action in load_actions():
        name = action.get("name", "(unknown)")
        with st.expander(name, expanded=False):
            st.toggle("Published", value=True, key=f"pub_{name}")
            st.write(action.get("description", ""))
            st.checkbox("LLM tested", value=False, key=f"llm_{name}")
            if st.button("Ping now", key=f"ping_{name}"):
                result = ping_action(base_url, action)
                st.code(json.dumps(result, indent=2), language="json")


if __name__ == "__main__":
    main()
