"""Streamlit component for managing indicator activation per symbol.

This component reads the :class:`~core.indicators.registry.IndicatorRegistry`
to discover available indicators. Indicators are grouped by their ``category``
field (falling back to ``"General"`` when unspecified) and presented with
checkboxes allowing the user to enable or disable each indicator for a given
stream and symbol.

Selections are persisted to a configuration store. When Redis is available the
configuration is saved as JSON under the key ``config:indicators:<symbol>`` so
that the enrichment pipeline can consume it. If Redis is unavailable a YAML
file at ``config/indicator_overrides.yml`` is used instead. The YAML structure
mirrors the Redis payload::

    <stream>:
      <symbol>:
        enabled:
          - rsi
          - macd

"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, List

import streamlit as st
import yaml

from core.indicators.registry import IndicatorRegistry

CONFIG_FILE = Path("config/indicator_overrides.yml")


def _load_yaml_config() -> Dict[str, Any]:
    """Return the YAML config as a dictionary if the file exists."""
    if CONFIG_FILE.exists():
        with CONFIG_FILE.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def _save_yaml_config(data: Dict[str, Any]) -> None:
    """Persist ``data`` to ``CONFIG_FILE`` in YAML format."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with CONFIG_FILE.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f)


def indicator_admin() -> None:
    """Render the indicator administration panel."""
    registry = IndicatorRegistry()

    st.header("Indicator Administration")
    stream = st.text_input("Stream", value="default")
    symbol = st.text_input("Symbol", value="AAPL").upper().strip()

    available = registry.get_all_available()

    # Group indicators by category
    grouped: Dict[str, List[tuple[str, Dict[str, Any]]]] = {}
    for ind_id, details in available.items():
        category = details.get("category", "General")
        grouped.setdefault(category, []).append((ind_id, details))

    active = set(registry.get_active_indicators(symbol))

    for category, indicators in grouped.items():
        with st.expander(category.title(), expanded=True):
            for ind_id, details in indicators:
                label = details.get("name", ind_id)
                key = f"{symbol}:{ind_id}"
                enabled = st.checkbox(label, value=ind_id in active, key=key)
                if enabled:
                    active.add(ind_id)
                else:
                    active.discard(ind_id)

    if st.button("Save"):
        payload = {"enabled": sorted(active)}
        if registry.redis_client:
            registry.redis_client.set(
                f"config:indicators:{symbol}", json.dumps(payload)
            )
            st.success(f"Saved configuration for {symbol} to Redis")
        else:
            cfg = _load_yaml_config()
            cfg.setdefault(stream, {})[symbol] = payload
            _save_yaml_config(cfg)
            st.success(
                f"Saved configuration for {stream}/{symbol} to {CONFIG_FILE}"
            )
