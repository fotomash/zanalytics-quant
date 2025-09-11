import plotly.graph_objects as go


def create_behavioral_donut(value: float, title: str, color: str, max_value: float = 100) -> go.Figure:
    """Create a donut-style gauge figure for behavioral metrics.

    Parameters
    ----------
    value : float
        The metric value to display on the gauge.
    title : str
        Label shown below the number.
    color : str
        Color used for the gauge's progress bar.
    max_value : float, optional
        Maximum possible value for the gauge, by default 100.

    Returns
    -------
    go.Figure
        Configured Plotly figure representing the donut gauge.
    """
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            title={"text": title},
            domain={"x": [0, 1], "y": [0, 1]},
            gauge={
                "axis": {"range": [0, max_value], "visible": False},
                "bar": {"color": color, "thickness": 0.3},
                "bgcolor": "rgba(0,0,0,0)",
                "bordercolor": "rgba(0,0,0,0)",
            },
__all__ = ["create_metric_donut"]


def create_metric_donut(value, title, color, suffix="%", max_value=100):
    """Return a Plotly indicator gauge rendered as a donut chart.

    Parameters
    ----------
    value: float
        Current value to display.
    title: str
        Title shown above the number.
    color: str
        Colour of the filled portion of the gauge.
    suffix: str, optional
        Text appended to the number (defaults to ``%``).
    max_value: float, optional
        Maximum value for the gauge (defaults to ``100``).
    """
    try:
        val = float(value)
    except (TypeError, ValueError):
        val = 0.0
    val = max(0.0, min(val, float(max_value)))

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=val,
            number={"suffix": suffix, "font": {"size": 24}},
            gauge={
                "axis": {"range": [0, max_value], "visible": False},
                "bar": {"color": color, "thickness": 0.4},
                "bgcolor": "rgba(0,0,0,0)",
                "borderwidth": 0,
            },
            domain={"x": [0, 1], "y": [0, 1]},
            title={"text": title, "font": {"size": 14}},
        )
    )
    fig.update_layout(
        margin=dict(t=0, b=0, l=0, r=0),
        height=140,
        width=140,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig

