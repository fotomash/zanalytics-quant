"""Streamlit launcher for the info dashboard.

This multipage app scans ``docs/wiki`` for Markdown files and
``dashboards/info/pages`` for Python modules exposing a ``render``
function.  Sidebar controls allow switching between procedural
Markdown docs and interactive pages.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import streamlit as st

# Paths
ROOT = Path(__file__).resolve().parents[2]
PAGES_DIR = Path(__file__).parent / "pages"
DOCS_DIR = ROOT / "docs" / "wiki"


def discover_pages() -> dict[str, object]:
    """Import all page modules that expose a ``render`` function."""
    pages: dict[str, object] = {}
    for path in sorted(PAGES_DIR.glob("*.py")):
        if path.name in {"__init__.py", "utils.py"}:
            continue
        module_name = f"{__package__}.pages.{path.stem}"
        module = importlib.import_module(module_name)
        if hasattr(module, "render"):
            pages[path.stem] = module
    return pages


def discover_docs() -> dict[str, Path]:
    """Return available markdown documents."""
    if not DOCS_DIR.exists():
        return {}
    return {p.stem: p for p in sorted(DOCS_DIR.glob("*.md"))}


# Simple mock data used by pages
MOCK_DATA = {
    "system_status": {"heartbeat": "Active", "lag_ms": 150},
    "behavioral_metrics": {
        "discipline": 87,
        "patience": 142,
        "conviction": 73,
        "efficiency": 68,
    },
    "confluence_score": 78,
    "strategies": [
        {
            "name": "SMC Liquidity Sweep",
            "setup": "Identify order blocks and fair value gaps",
            "signals": "BOS/CHOCH confirmation with volume imbalance",
            "confluence": "70-100: High; 50-69: Medium",
            "bias": "Entry on sweep; Exit at opposing block",
            "risk_gates": "Discipline >70, Patience >120s",
            "journal_hook": "Record BOS level and imbalance direction",
        }
    ],
    "journal_entries": [
        {
            "ts": "2025-09-10T10:15:00Z",
            "kind": "ENTRY",
            "text": "XAUUSD long on SMC sweep",
            "meta": {"confluence": 82},
        },
        {
            "ts": "2025-09-10T11:30:00Z",
            "kind": "PARTIAL_CLOSE",
            "text": "50% profit take",
            "meta": {"pnl": 450},
        },
    ],
}


PAGES = discover_pages()
DOCS = discover_docs()

mode = st.sidebar.radio("Content", ["Pages", "Docs"])

if mode == "Pages" and PAGES:
    page_name = st.sidebar.selectbox("Page", sorted(PAGES))
    page_mod = PAGES[page_name]
    page_mod.render(MOCK_DATA)
elif mode == "Docs" and DOCS:
    doc_name = st.sidebar.selectbox("Doc", sorted(DOCS))
    st.markdown(DOCS[doc_name].read_text(), unsafe_allow_html=False)
else:
    st.write("No content available.")
