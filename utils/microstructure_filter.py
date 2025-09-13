
import pandas as pd


def microstructure_filter(
    df: pd.DataFrame,
    spread_column: str = "spread",
    liquidity_column: str = "liquidity_score",
    *,
    max_spread: float = 0.05,
    min_liquidity: float = 0.0,
) -> pd.DataFrame:
    """Filter out observations with poor market microstructure.


    Parameters
    ----------
    df:
        DataFrame containing microstructure metrics.
    spread_column:
        Name of the column with spread values.  Rows with spreads greater
        than ``max_spread`` are removed.
    liquidity_column:
        Name of the column with liquidity scores.  Rows with liquidity
        scores lower than ``min_liquidity`` are removed.
    max_spread:
        Maximum acceptable spread.  Defaults to ``0.05``.
    min_liquidity:
        Minimum acceptable liquidity score.  Defaults to ``0.0``.

    Returns
    -------
    pd.DataFrame
        Filtered DataFrame containing only rows that satisfy the
        microstructure quality thresholds.  If the required columns are
        missing, the input DataFrame is returned unchanged.
    """

    if spread_column not in df.columns or liquidity_column not in df.columns:
        return df

    mask = (df[spread_column] <= max_spread) & (df[liquidity_column] >= min_liquidity)
    return df.loc[mask].copy()
