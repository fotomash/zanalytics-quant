import os, json
from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


# -----------------------------------------------------------------------------
# Cached connections
# -----------------------------------------------------------------------------
@st.experimental_singleton(show_spinner=False)
def get_redis_client() -> Optional[Any]:
    """Return a cached Redis client if Redis is available."""
    try:  # import inside to avoid hard dependency during tests
        import redis  # type: ignore
    except Exception:  # pragma: no cover - redis optional
        return None

    try:
        client = redis.Redis(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            decode_responses=True,
        )
        client.ping()
        return client
    except Exception:
        return None


@st.experimental_singleton(show_spinner=False)
def get_kafka_consumer() -> Optional[Any]:
    """Return a cached Kafka consumer if Kafka configuration is present."""
    broker = os.getenv("KAFKA_BROKER")
    if not broker:
        return None
    try:  # pragma: no cover - confluent_kafka optional
        from confluent_kafka import Consumer  # type: ignore
    except Exception:
        return None

    conf = {
        "bootstrap.servers": broker,
        "group.id": "pulse-dashboard",
        "auto.offset.reset": "latest",
    }
    try:
        consumer = Consumer(conf)
        topic = os.getenv("KAFKA_TOPIC", "harmonics")
        consumer.subscribe([topic])
        return consumer
    except Exception:
        return None


# -----------------------------------------------------------------------------
# Data fetching (cached for snappy load times)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=1.0, show_spinner=False)
def fetch_latest_message() -> Optional[Dict[str, Any]]:
    """Fetch the most recent harmonic payload from Redis or Kafka."""
    client = get_redis_client()
    if client is not None:
        try:
            entries = client.xrevrange("harmonics", count=1)
            if entries:
                data = entries[0][1].get("data")
                if data:
                    return json.loads(data)
        except Exception:
            pass

    consumer = get_kafka_consumer()
    if consumer is not None:
        try:
            msg = consumer.poll(timeout=0.1)
            if msg is not None and msg.value():
                return json.loads(msg.value().decode("utf-8"))
        except Exception:
            pass
    return None


# -----------------------------------------------------------------------------
# Chart utilities (adapted from dashboard/_mix/🧠 SMC.py)
# -----------------------------------------------------------------------------


def render_harmonic_chart(
    df: pd.DataFrame, patterns: List[Dict[str, Any]]
) -> go.Figure:
    """Render OHLC chart with harmonic overlays and PRZ shading."""
    fig = go.Figure(
        data=[
            go.Candlestick(
                x=df.index,
                open=df["open"],
                high=df["high"],
                low=df["low"],
                close=df["close"],
                name="Price",
            )
        ]
    )

    for pattern in patterns:
        # Connect pattern points (same logic as SMCChartGenerator)
        points_x = [
            pd.to_datetime(pattern.get(f"point{i}_time"))
            for i in range(1, 6)
            if pattern.get(f"point{i}_time")
        ]
        points_y = [
            pattern.get(f"point{i}_price")
            for i in range(1, 6)
            if pattern.get(f"point{i}_price") is not None
        ]
        if len(points_x) >= 2 and len(points_x) == len(points_y):
            fig.add_trace(
                go.Scatter(
                    x=points_x,
                    y=points_y,
                    mode="lines+markers",
                    line=dict(color="#9b59b6", width=2),
                    marker=dict(size=8),
                    name=f"Harmonic: {pattern.get('pattern_type', 'Unknown')}",
                )
            )

        # PRZ shading
        prz_low = pattern.get("prz_low")
        prz_high = pattern.get("prz_high")
        if prz_low is not None and prz_high is not None:
            fig.add_shape(
                type="rect",
                x0=df.index[0],
                x1=df.index[-1],
                y0=prz_low,
                y1=prz_high,
                fillcolor="rgba(255,0,0,0.1)",
                line=dict(width=0),
            )

    fig.update_layout(margin=dict(l=0, r=0, t=30, b=20))
    return fig


# -----------------------------------------------------------------------------
# Streamlit page
# -----------------------------------------------------------------------------

st.set_page_config(page_title="Pulse Harmonics", layout="wide")
st.title("🔔 Pulse Harmonic Monitor")

payload = fetch_latest_message()

if payload is None:
    st.info("No harmonic data available from streams.")
    st.stop()

# Prepare dataframe
ohlc = pd.DataFrame(payload.get("ohlc", []))
if "time" in ohlc.columns:
    ohlc["time"] = pd.to_datetime(ohlc["time"])
    ohlc.set_index("time", inplace=True)

patterns: List[Dict[str, Any]] = payload.get("harmonic_patterns", [])

fig = render_harmonic_chart(ohlc, patterns)
st.plotly_chart(fig, use_container_width=True)

# -----------------------------------------------------------------------------
# Alerting panel
# -----------------------------------------------------------------------------
alerts = [p for p in patterns if p.get("confidence", 0) > 0.7]

st.subheader("Alerts")
if not alerts:
    st.write("No high-confidence harmonic patterns detected.")
else:
    enable_audio = st.checkbox("Audio alerts", value=False)
    for patt in alerts:
        st.warning(
            f"{patt.get('pattern_type', 'Pattern')} with confidence "
            f"{patt.get('confidence', 0):.2f}"
        )
    if enable_audio:
        st.audio(
            "https://actions.google.com/sounds/v1/alarms/beep_short.ogg",
            autoplay=True,
        )
