import json
from pathlib import Path
import streamlit as st


@st.cache_data
def load_strategies():
    """Load strategy JSON files from the strategies directory.

    Each JSON file is expected to contain a dictionary. The filename is
    attached to the resulting dictionary under the key ``__filename__``.

    Malformed JSON files or unreadable files are skipped. Missing fields inside
    a strategy do not raise errors; they simply remain absent in the returned
    dict.
    """
    strategies_dir = Path(__file__).resolve().parents[2] / "knowledge" / "strategies"
    strategies = []

    if not strategies_dir.exists():
        st.warning(f"Strategies directory not found: {strategies_dir}")
        return strategies

    for path in strategies_dir.rglob("*.json"):
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                st.warning(f"{path.name} does not contain a JSON object; skipping.")
                continue
        except (json.JSONDecodeError, OSError) as exc:
            st.warning(f"Failed to load {path.name}: {exc}")
            continue

        # Attach filename and append to the list
        data.setdefault("__filename__", path.name)
        strategies.append(data)

    return strategies
