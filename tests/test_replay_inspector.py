import json
from pathlib import Path

import pandas as pd

from replay_inspector import ReplayInspector, score_embedding


def _create_parquet(path: Path) -> Path:
    df = pd.DataFrame(
        [
            {"symbol": "BTC", "confidence": 0.9, "embedding": [0.1, 0.2]},
            {"symbol": "BTC", "confidence": 0.8, "embedding": [0.3, 0.4]},
            {"symbol": "ETH", "confidence": 0.7, "embedding": [0.5, 0.6]},
        ]
    )
    out = path / "ticks.parquet"
    df.to_parquet(out)
    return out


def test_filter_aggregate_and_export(tmp_path, monkeypatch):
    parquet_path = _create_parquet(tmp_path)

    def fake_score(emb):
        return {"metric": round(sum(emb), 2)}

    monkeypatch.setattr("replay_inspector.score_embedding", fake_score)

    insp = ReplayInspector(parquet_path)
    filtered = insp.filter(symbol="BTC", min_conf=0.8)
    assert len(filtered) == 2

    agg = insp.aggregate(filtered)
    expected = pd.DataFrame(
        [{"symbol": "BTC", "confidence": 0.85, "metric": 0.5}]
    )
    pd.testing.assert_frame_equal(agg, expected)

    csv_path = tmp_path / "out.csv"
    json_path = tmp_path / "out.json"
    insp.to_csv(agg, csv_path)
    insp.to_json(agg, json_path)

    csv_df = pd.read_csv(csv_path)
    pd.testing.assert_frame_equal(csv_df, expected)

    with open(json_path) as fh:
        data = json.load(fh)
    assert data == [{"symbol": "BTC", "confidence": 0.85, "metric": 0.5}]
