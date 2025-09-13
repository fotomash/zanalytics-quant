"""SMC feature extraction utilities.

The :func:`run` function is intentionally lightweight; it operates on a
plain ``dict`` of OHLC values and returns a tuple containing a features
dictionary and, when possible, a vector representation of those features.
"""

from __future__ import annotations

from typing import Optional


def run(data: dict) -> tuple[dict, Optional[list[float]]]:
    """Extract simple SMC features.

    Parameters
    ----------
    data:
        Mapping containing ``open``, ``high``, ``low`` and ``close`` prices.

    Returns
    -------
    tuple[dict, Optional[list[float]]]
        A tuple of ``(features, vector)`` where ``features`` is a dictionary of
        derived metrics. ``vector`` is a list of floats suitable for similarity
        search or further analysis. If the required OHLC fields are missing,
        ``vector`` will be ``None``.
    """

    open_price = data.get("open")
    high = data.get("high")
    low = data.get("low")
    close = data.get("close")

    features: dict[str, float | bool] = {}
    vector: Optional[list[float]] = None

    if None not in (open_price, high, low, close):
        range_val = float(high) - float(low)
        midpoint = (float(high) + float(low)) / 2
        body = float(close) - float(open_price)
        is_bullish = float(close) > float(open_price)

        features = {
            "range": range_val,
            "midpoint": midpoint,
            "body": body,
            "is_bullish": is_bullish,
        }

        vector = [range_val, midpoint, body, 1.0 if is_bullish else 0.0]
    else:
        # Return whatever values are available to aid debugging
        features = {k: data[k] for k in ("open", "high", "low", "close") if k in data}

    return features, vector


__all__ = ["run"]

