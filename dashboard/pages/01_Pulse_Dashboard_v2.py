"""Pulse dashboard Streamlit page v2."""

import streamlit as st


def render_pnl_metric(live_data: dict) -> None:
    """Render today's P&L metric using Streamlit.

    Parameters
    ----------
    live_data: dict
        Dictionary containing ``pnl_today`` and ``pnl_change`` keys.
    """
    st.metric(
        label="Today's P&L",
        value=f"${live_data['pnl_today']:,.2f}",
        delta=live_data['pnl_change'],
        delta_color="normal",
    )


if __name__ == "__main__":
    sample = {"pnl_today": 1250.75, "pnl_change": -50.25}
    render_pnl_metric(sample)
