from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd


def score_embedding(embedding: Sequence[float]) -> dict:
    """Placeholder embedding scoring function.

    The real implementation computes various similarity metrics for an embedding
    vector.  Tests patch this function to provide deterministic metrics.
    """

    return {"score": float(sum(embedding))}


class ReplayInspector:
    """Inspect enriched tick data stored in Parquet files.

    The inspector loads one or more Parquet files containing enriched ticks and
    provides helpers for filtering, aggregating and exporting summary data.
    """

    def __init__(self, paths: Iterable[Path | str]):
        if isinstance(paths, (str, Path)):
            paths = [paths]
        self._df = pd.concat(
            [pd.read_parquet(Path(p)) for p in paths], ignore_index=True
        )

    @property
    def dataframe(self) -> pd.DataFrame:
        """Return the loaded dataframe."""

        return self._df

    def filter(
        self, *, symbol: str | None = None, min_conf: float | None = None
    ) -> pd.DataFrame:
        """Return a filtered copy of the loaded dataframe."""

        df = self._df
        if symbol is not None:
            df = df[df["symbol"] == symbol]
        if min_conf is not None:
            df = df[df["confidence"] >= min_conf]
        return df.reset_index(drop=True)

    def aggregate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate metrics for a dataframe of ticks.

        ``score_embedding`` is applied to the ``embedding`` column and the
        resulting metrics are averaged per symbol along with the confidence.
        """

        metrics = df["embedding"].apply(score_embedding).apply(pd.Series)
        df = df.drop(columns=["embedding"]).join(metrics)
        numeric_cols = df.select_dtypes(include="number").columns
        agg = df.groupby("symbol")[numeric_cols].mean().reset_index()
        return agg

    @staticmethod
    def to_csv(df: pd.DataFrame, path: Path | str) -> None:
        df.to_csv(path, index=False)

    @staticmethod
    def to_json(df: pd.DataFrame, path: Path | str) -> None:
        df.to_json(path, orient="records", indent=2)
