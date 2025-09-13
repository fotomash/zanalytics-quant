#!/usr/bin/env python3
"""Inspect tick replays with analog scoring.

This CLI loads a Parquet file of tick or bar data, optionally filters the
rows, enriches the resulting DataFrame and performs analog scoring using the
vector subsystem.  The scoring can be seeded with a text query or defaults to
the first row in the dataset.

Examples
--------
python scripts/replay_inspector.py path/to/data.parquet \
       --filter "symbol == 'EURUSD'" --query "spike down" --top 3
"""
from __future__ import annotations

import argparse
from typing import Iterable, List, Sequence, Tuple

import numpy as np
import pandas as pd

from enrichment.enrichment_engine import ensure_dataframe
from services.mcp2.vector.embeddings import embed

try:  # allow running as a script or module
    from .replay_inspector_lib import ReplayInspector
except Exception:  # pragma: no cover - fallback for script execution
    from replay_inspector_lib import ReplayInspector
try:  # optional faiss integration
    from services.mcp2.vector import FaissStore  # type: ignore
except Exception:  # pragma: no cover - faiss not installed
    FaissStore = None  # type: ignore


def _row_text(row: pd.Series, columns: Sequence[str]) -> str:
    parts = [str(row[c]) for c in columns if c in row and pd.notna(row[c])]
    return " ".join(parts)


def embed_rows(df: pd.DataFrame, columns: Sequence[str]) -> List[List[float]]:
    """Return embeddings for each row in ``df`` using ``columns``."""
    texts = [_row_text(row, columns) for _, row in df.iterrows()]
    return [embed(text) for text in texts]


def analog_scores(
    embeddings: Sequence[Sequence[float]],
    query_vec: Sequence[float],
    top_k: int = 5,
) -> List[Tuple[int, float]]:
    """Return ``top_k`` indices with cosine similarity to ``query_vec``."""
    emb = np.array(embeddings, dtype=float)
    q = np.array(query_vec, dtype=float)
    if emb.size == 0:
        return []
    norms = np.linalg.norm(emb, axis=1) * np.linalg.norm(q)
    norms = np.where(norms == 0, 1e-9, norms)
    scores = (emb @ q) / norms
    idx = np.argsort(-scores)[:top_k]
    return [(int(i), float(scores[i])) for i in idx]


def run_analog_scoring(
    df: pd.DataFrame, columns: Sequence[str], query: str | None, top_k: int
) -> List[Tuple[int, float]]:
    """Compute analog scores for ``df`` using optional ``query`` text."""
    embeds = embed_rows(df, columns)
    q_vec = embed(query) if query else embeds[0]

    if FaissStore is not None:
        store = FaissStore(len(q_vec), max_size=len(embeds))  # type: ignore
        for idx, (vec, payload) in enumerate(zip(embeds, df.to_dict(orient="records"))):
            store._add(idx, vec, payload)  # type: ignore - using sync helper
        result = store._query(q_vec, top_k=top_k)["matches"]  # type: ignore
        return [(int(r["id"]), float(r["distance"])) for r in result]

    return analog_scores(embeds, q_vec, top_k=top_k)


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Inspect Parquet replay with analog scoring"
    )
    parser.add_argument("path", help="Path to Parquet file")
    parser.add_argument("--filter", dest="filter_expr", help="pandas query expression")
    parser.add_argument(
        "--columns", nargs="*", default=None, help="Columns used for embeddings"
    )
    parser.add_argument("--query", help="Seed text for analog scoring")
    parser.add_argument("--top", type=int, default=5, help="Number of results to show")
    args = parser.parse_args(list(argv) if argv is not None else None)

    inspector = ReplayInspector(args.path)
    df = inspector.dataframe
    if args.filter_expr:
        try:
            df = df.query(args.filter_expr)
        except Exception:  # pragma: no cover - defensive
            pass
    state = {"dataframe": df}
    df = ensure_dataframe(state) or pd.DataFrame()
    if df.empty:
        raise SystemExit("no data after filtering")

    columns = args.columns or list(df.columns)
    scores = run_analog_scoring(df, columns, args.query, args.top)
    for idx, score in scores:
        print(f"row={idx} score={score:.4f}")


if __name__ == "__main__":  # pragma: no cover
    main()
