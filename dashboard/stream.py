"""Minimal Streamlit viewer for MCP2 WebSocket streams.

The app connects to the configured WebSocket endpoint and updates a
placeholder with incoming JSON messages without blocking the UI. Set
``LIVE_DATA_WS_URL`` to point at the MCP2 WebSocket server.

Run with:
    streamlit run dashboard/stream.py
"""

from __future__ import annotations

import streamlit as st

from .utils import ws


st.set_page_config(page_title="MCP2 Stream", layout="wide")
st.title("MCP2 Live Stream")

placeholder = st.empty()


def _handle(message: dict) -> None:
    placeholder.json(message)


# Subscribe in a background thread so the Streamlit event loop remains
# responsive. The default topic "trades" can be overridden via URL query
# parameters when launching the app.
topic = st.experimental_get_query_params().get("topic", ["trades"])[0]
ws.subscribe(topic, _handle)

st.caption("Connected to MCP2 via WebSocket")

