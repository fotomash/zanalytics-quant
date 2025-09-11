import pandas as pd
import plotly.graph_objects as go
from typing import Dict, Any


def create_enhanced_wyckoff_chart(df: pd.DataFrame, analysis: Dict[str, Any], symbol: str) -> go.Figure:
    """Create a Wyckoff price chart annotated with analysis results.

    Parameters
    ----------
    df : pandas.DataFrame
        Price data indexed by timestamp and containing ``open``, ``high``, ``low``
        and ``close`` columns.
    analysis : Dict[str, Any]
        Output produced by the Wyckoff analysis engine.  Expected keys include
        ``events`` (a list of mapping objects with ``time``, ``price`` and ``type``)
        and optionally ``phases`` (a list of mapping objects with ``start``,
        ``end`` and ``phase``).
    symbol : str
        Market symbol used in the chart title.

    Returns
    -------
    go.Figure
        A Plotly figure containing a candlestick chart with annotated Wyckoff
        phases and events.
    """
    fig = go.Figure(
        go.Candlestick(
            x=df.index,
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="Price",
        )
    )

    # Highlight Wyckoff phases if provided
    for phase in analysis.get("phases", []):
        start = phase.get("start")
        end = phase.get("end")
        label = phase.get("phase", "")
        if start is not None and end is not None:
            fig.add_vrect(
                x0=start,
                x1=end,
                fillcolor="rgba(255, 165, 0, 0.1)",
                line_width=0,
            )
            fig.add_annotation(
                x=(start + (end - start) / 2),
                y=df["high"].max(),
                text=label,
                showarrow=False,
                bgcolor="rgba(0,0,0,0.6)",
                font=dict(color="white", size=10),
            )

    # Annotate Wyckoff events
    for event in analysis.get("events", []):
        fig.add_annotation(
            x=event.get("time"),
            y=event.get("price"),
            text=event.get("type", ""),
            showarrow=True,
            arrowhead=2,
            ax=0,
            ay=-30,
            bgcolor="rgba(0,0,0,0.6)",
            font=dict(color="white", size=10),
        )

    fig.update_layout(
        title=f"Enhanced Wyckoff Analysis – {symbol}",
        xaxis_title="Time",
        yaxis_title="Price",
        template="plotly_dark",
    )

    return fig
