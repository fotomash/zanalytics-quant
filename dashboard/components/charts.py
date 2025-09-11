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
        )
    )
    fig.update_layout(
        margin=dict(t=0, b=0, l=0, r=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig

