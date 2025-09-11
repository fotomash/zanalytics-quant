import re
from pathlib import Path
import streamlit as st


def _normalize_filename(name: str) -> str:
    """Replace non-word characters with underscores."""
    return re.sub(r"\W+", "_", name)

__filename__ = Path(__file__).stem
sanitized_filename = _normalize_filename(__filename__)

session_state_key = f"{sanitized_filename}_session"
if session_state_key not in st.session_state:
    st.session_state[session_state_key] = {}

st.title("Strategy Explorer v3")

if st.button("Reset", key=f"{sanitized_filename}_reset"):
    st.session_state[session_state_key] = {}
    st.success("Session state reset.")
