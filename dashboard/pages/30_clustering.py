import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Vector Clustering", layout="wide")


def _load_sample_vectors():
    """Return a small sample of clustered vectors.

    Each vector contains ``x`` and ``y`` coordinates along with metadata
    describing the pattern name, realised PnL and confidence score.  In the
    real application these would be sourced from the vector database.
    """
    return [
        {
            "x": 0.1,
            "y": 0.2,
            "metadata": {
                "pattern_name": "Bullish ABC",
                "pnl": 1500.0,
                "confidence": 0.87,
            },
        },
        {
            "x": -0.3,
            "y": 0.4,
            "metadata": {
                "pattern_name": "Bearish XYZ",
                "pnl": -250.5,
                "confidence": 0.65,
            },
        },
    ]


def _build_dataframe(vectors):
    """Transform vector list into a DataFrame for plotting."""
    rows = []
    for vec in vectors:
        meta = vec.get("metadata", {})
        rows.append(
            {
                "x": vec.get("x"),
                "y": vec.get("y"),
                "pattern_name": meta.get("pattern_name"),
                "pnl": meta.get("pnl"),
                "confidence": meta.get("confidence"),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    st.title("Clustering")

    vectors = _load_sample_vectors()
    df = _build_dataframe(vectors)

    fig = px.scatter(
        df,
        x="x",
        y="y",
        custom_data=["pattern_name", "pnl", "confidence"],
    )
    fig.update_traces(
        hovertemplate="Pattern: %{customdata[0]}<br>PnL: %{customdata[1]:,.2f}<br>Confidence: %{customdata[2]:.2f}<extra></extra>"
    )
    st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    main()
