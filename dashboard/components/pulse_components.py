from enum import Enum
from typing import Iterable, Mapping, Any

import streamlit as st


class OrderSide(Enum):
    """Human friendly order side identifiers."""
    BUY = 0
    SELL = 1


def render_positions_expander(title: str, positions: Iterable[Mapping[str, Any]]) -> None:
    """Render position details inside an expander.

    Parameters
    ----------
    title:
        Title for the expander.
    positions:
        Iterable of mapping objects containing position information.
    """
    with st.expander(title):
        positions = list(positions or [])
        if not positions:
            st.write("No open positions")
            return

        for index, position in enumerate(positions):
            symbol = position.get("symbol", "Unknown")
            volume = position.get("volume", 0)
            entry_price = position.get("entry_price", 0.0)
            side_code = position.get("type", OrderSide.BUY.value)
            try:
                side = OrderSide(side_code)
            except ValueError:
                side = None

            side_label = side.name if side else "UNKNOWN"
            st.write(f"{symbol} {side_label} {volume} @ {entry_price}")

            # place divider only between positions
            if index < len(positions) - 1:
                st.divider()
