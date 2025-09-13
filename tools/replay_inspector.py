"""Inspect enriched replay data and produce vector-based metrics.

The script loads one or more Parquet files containing replay enrichment
results, fetches tick embeddings, and evaluates them against historical
vectors stored in Qdrant.  Aggregated metrics are emitted as either CSV or
JSON while a concise summary is printed to the console.
"""

from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

import pandas as pd

from utils.enrich import get_embedding
from utils import vector_backtester


def _load_parquet(path_pattern: str) -> pd.DataFrame:
    paths = sorted(
        p
        for pattern in [path_pattern]
        for p in glob.glob(pattern)
        if Path(p).suffix == ".parquet"
    )
    if not paths:
        raise FileNotFoundError(f"No Parquet files match {path_pattern}")
    frames = [pd.read_parquet(p) for p in paths]
    return pd.concat(frames, ignore_index=True)


def _apply_filter(df: pd.DataFrame, enrichment: str | None) -> pd.DataFrame:
    if not enrichment:
        return df
    for col in ("enrichment_type", "phase", "enrichment_phase", "type"):
        if col in df.columns:
            return df[df[col] == enrichment]
    return df


def _score_rows(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    scored: List[Dict[str, Any]] = []
    for row in rows:
        embedding_id = row.get("embedding_id")
        if not embedding_id:
            continue
        embedding = get_embedding(embedding_id)
        if not embedding:
            continue
        pnl, win_rate, payloads = vector_backtester.score_embedding(embedding)
        batch = row.get("batch_id") or row.get("batch") or 0
        scored.append(
            {
                "batch": batch,
                "tick_id": row.get("tick_id"),
                "pnl": pnl,
                "win_rate": win_rate,
                "payloads": payloads,
            }
        )
    return scored


def _aggregate(scored: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not scored:
        return []
    df = pd.DataFrame(scored)
    grouped = df.groupby("batch").agg({"pnl": "mean", "win_rate": "mean"}).reset_index()
    output: List[Dict[str, Any]] = []
    for row in grouped.itertuples(index=False):
        payloads = df[df["batch"] == row.batch]["payloads"].explode().dropna().tolist()
        output.append(
            {
                "batch": row.batch,
                "avg_pnl": float(row.pnl),
                "win_rate": float(row.win_rate),
                "payloads": payloads,
            }
        )
    return output


def _save(data: List[Dict[str, Any]], fmt: str, path: Path) -> None:
    if fmt == "csv":
        pd.DataFrame(data).to_csv(path, index=False)
    else:
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input",
        nargs="?",
        default="/data/enriched/*.parquet",
        help="Input Parquet path or glob",
    )
    parser.add_argument("--enrichment", help="Filter rows by enrichment phase or type")
    parser.add_argument(
        "--format", choices=["csv", "json"], default="json", help="Output format"
    )
    parser.add_argument(
        "--output", default="replay_metrics.out", help="Output file path"
    )
    args = parser.parse_args(argv)

    df = _apply_filter(_load_parquet(args.input), args.enrichment)
    scored = _score_rows(df.to_dict("records"))
    aggregated = _aggregate(scored)

    out_path = Path(args.output)
    _save(aggregated, args.format, out_path)

    for item in aggregated:
        print(
            f"Batch {item['batch']}: avg_pnl={item['avg_pnl']:.4f}, win_rate={item['win_rate']:.2%}, matches={len(item['payloads'])}"
        )


if __name__ == "__main__":  # pragma: no cover - manual execution
    main()
