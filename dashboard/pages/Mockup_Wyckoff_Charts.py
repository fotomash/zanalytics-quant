import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import streamlit as st

from dashboard.styles.main_st_style import apply_main_styling

# Page configuration to match existing dashboard conventions
st.set_page_config(
    page_title="Mockup Wyckoff Charts",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply shared styling
st.markdown(apply_main_styling(), unsafe_allow_html=True)


@st.cache_data
def generate_mock_data(rows: int = 100) -> pd.DataFrame:
    """Generate mock OHLCV data for demonstration purposes."""
    start = datetime.now() - timedelta(minutes=rows)
    times = [start + timedelta(minutes=i) for i in range(rows)]
    base = np.cumsum(np.random.randn(rows)) + 100
    opens = base + np.random.randn(rows) * 0.5
    closes = base + np.random.randn(rows) * 0.5
    highs = np.maximum(opens, closes) + np.random.rand(rows)
    lows = np.minimum(opens, closes) - np.random.rand(rows)
    volume = np.random.randint(100, 1000, size=rows)

    return pd.DataFrame(
        {
            "time": times,
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": volume,
        }
    )


st.title("Wyckoff Charts Mockup")

st.markdown(
    """
    This demo page shows how Wyckoff-style charts could be integrated into the dashboard.

    **Usage**
    1. Adjust the number of data points from the sidebar.
    2. The app generates mock OHLCV data.
    3. A candlestick chart renders the mock data.

    Use this page as a starting point when wiring real data sources into the dashboard.
    """
)

# Sidebar controls
st.sidebar.header("Mock Data Options")
points = st.sidebar.slider("Data points", min_value=50, max_value=300, value=150, step=10)

# Generate mock data and plot
mock_df = generate_mock_data(points)

fig = go.Figure(
    data=[
        go.Candlestick(
            x=mock_df["time"],
            open=mock_df["open"],
            high=mock_df["high"],
            low=mock_df["low"],
            close=mock_df["close"],
            name="Price",
        )
    ]
)
fig.update_layout(margin=dict(l=0, r=0, t=40, b=0), height=600)

st.plotly_chart(fig, use_container_width=True)

st.caption("Generated data is random and for illustrative purposes only.")
