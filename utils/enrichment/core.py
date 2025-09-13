import pandas as pd
import numpy as np

TIMEFRAME_RULES = {
    "M1": "1T",
    "M5": "5T",
    "M15": "15T",
    "M30": "30T",
    "H1": "1H",
    "H4": "4H",
    "D1": "1D",
    "W1": "1W",
    "MN1": "1M",
}


def aggregate_ticks_to_bars(ticks: pd.DataFrame, timeframe: str = "M1") -> pd.DataFrame:
    """Aggregate tick data into OHLC bars using pandas resample.

    Parameters
    ----------
    ticks : pd.DataFrame
        DataFrame containing tick data. It must have either a ``timestamp``
        column or a datetime index along with a ``bid`` price column. If an
        ``ask`` column is present it will be used to compute the mid price.
    timeframe : str, default "M1"
        Target timeframe in MT5 format (e.g. ``M1``, ``M5``). A valid pandas
        resample string can also be provided.

    Returns
    -------
    pd.DataFrame
        Resampled bar data with ``open``, ``high``, ``low`` and ``close``
        columns. ``volume`` will be summed if present in the input ``ticks``.
    """

    if ticks is None or ticks.empty:
        return pd.DataFrame()

    df = ticks.copy()

    # Ensure datetime index
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df.set_index("timestamp", inplace=True)

    rule = TIMEFRAME_RULES.get(timeframe.upper(), timeframe)

    agg: dict[str, str | list[str]] = {"bid": ["first", "max", "min", "last"]}
    if "volume" in df.columns:
        agg["volume"] = "sum"

    resampled = df.resample(rule).agg(agg)
    resampled.columns = ["open", "high", "low", "close"] + (
        ["volume"] if "volume" in df.columns else []
    )

    resampled.dropna(subset=["open"], inplace=True)

    return resampled


def enrich_ticks(df: pd.DataFrame) -> pd.DataFrame:
    """Enrich tick or bar data with common metrics.

    The function expects ``bid`` and ``ask`` columns where available. When
    present, it derives ``mid_price`` and ``spread`` metrics. Simple
    technical indicators like rolling averages and returns are also
    calculated on the mid price.
    """
    if df is None or df.empty:
        return df

    df = df.copy()

    if {"bid", "ask"}.issubset(df.columns):
        df["mid_price"] = (df["bid"] + df["ask"]) / 2
        df["spread"] = df["ask"] - df["bid"]
        df["spread_bps"] = df["spread"] / df["bid"].replace(0, pd.NA) * 10000
    elif "close" in df.columns:
        df["mid_price"] = df["close"]
    elif "price" in df.columns:
        df["mid_price"] = df["price"]

    if "mid_price" in df.columns:
        df["return"] = df["mid_price"].pct_change()
        df["ma_5"] = df["mid_price"].rolling(5).mean()
        df["ma_20"] = df["mid_price"].rolling(20).mean()

    return df


def run(ticks: pd.DataFrame, timeframe: str = "M1") -> pd.DataFrame:
    """Aggregate ticks then enrich the resulting bars."""
    bars = aggregate_ticks_to_bars(ticks, timeframe)
    return enrich_ticks(bars)


__all__ = ["aggregate_ticks_to_bars", "enrich_ticks", "run"]
