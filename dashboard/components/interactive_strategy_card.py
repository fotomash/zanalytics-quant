import logging
from typing import Iterable, Mapping, Any

import streamlit as st

__all__ = ["render_interactive_strategy_card"]

logger = logging.getLogger(__name__)

REQUIRED_KEYS = ("display_text", "prompt_id", "required_data")
OPTIONAL_DEFAULTS = {"tooltip": ""}

def render_interactive_strategy_card(prompt_configs: Iterable[Mapping[str, Any]]) -> None:
    """Render an interactive strategy card.

    Parameters
    ----------
    prompt_configs:
        Iterable of mappings describing the prompts to render.  Each prompt must
        contain ``display_text``, ``prompt_id`` and ``required_data`` keys.
        ``tooltip`` is optional and defaults to an empty string.

    Prompts missing required keys are skipped and logged to avoid ``KeyError``.
    """
    for cfg in prompt_configs:
        if not isinstance(cfg, Mapping):
            logger.warning("Skipping prompt config that is not a mapping: %r", cfg)
            continue

        missing = [key for key in REQUIRED_KEYS if key not in cfg]
        if missing:
            logger.warning("Skipping prompt due to missing keys %s: %r", missing, cfg)
            continue

        for key, default in OPTIONAL_DEFAULTS.items():
            cfg.setdefault(key, default)

        display_text = cfg["display_text"]
        prompt_id = cfg["prompt_id"]
        tooltip = cfg.get("tooltip", "")

        st.button(display_text, key=prompt_id, help=tooltip)
