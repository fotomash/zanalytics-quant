from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Sequence

import math
import pandas as pd


def score_embedding(embedding: Sequence[float]) -> dict:
    """Return cosine similarity and distance for ``embedding``.

    The embedding is compared against a unit vector of the same dimensionality
    (a vector of ones).  This keeps the metric deterministic and independent of
    any external state while still exercising the typical cosine calculations
    used by the real system.
    """

    vec = list(embedding)
    if not vec:
        return {"cosine_similarity": 0.0, "cosine_distance": 1.0}

    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0:
        return {"cosine_similarity": 0.0, "cosine_distance": 1.0}

    ref_norm = math.sqrt(len(vec))  # norm of [1, 1, ..., 1]
    cos_sim = sum(vec) / (norm * ref_norm)
    cos_dist = 1.0 - cos_sim
    return {"cosine_similarity": cos_sim, "cosine_distance": cos_dist}


class ReplayInspector:
    """Inspect enriched tick data stored in Parquet files.

    The inspector loads one or more Parquet files containing enriched ticks and
    provides helpers for filtering, aggregating and exporting summary data.
    """

    def __init__(self, paths: Iterable[Path | str]):
        if isinstance(paths, (str, Path)):
            paths = [paths]
        self._df = pd.concat([pd.read_parquet(Path(p)) for p in paths], ignore_index=True)

    def filter(self, *, symbol: str | None = None, min_conf: float | None = None) -> pd.DataFrame:
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
