import json
import pandas as pd

from scripts import replay_inspector as ri
from scripts.replay_inspector_lib import ReplayInspector


def test_analog_scores_order():
    embeddings = [[1, 0], [0, 1], [1, 1]]
    query = [1, 0]
    result = ri.analog_scores(embeddings, query, top_k=2)
    assert result[0][0] == 0
    assert result[0][1] >= result[1][1]


def test_replay_inspector_roundtrip(tmp_path, monkeypatch):
    # deterministic embed: length of text as first dimension
    def fake_embed(text: str):
        return [float(len(text)), 0.0]

    monkeypatch.setattr(ri, "embed", fake_embed)

    df = pd.DataFrame(
        {
            "symbol": ["BTC"],
            "confidence": [0.85],
            "text": ["a"],
            "embedding": [[0.5]],
        }
    )
    parquet_path = tmp_path / "data.parquet"
    df.to_parquet(parquet_path)

    insp = ReplayInspector(parquet_path)
    agg = insp.aggregate(insp.filter())

    csv_path = tmp_path / "out.csv"
    json_path = tmp_path / "out.json"
    insp.to_csv(agg, csv_path)
    insp.to_json(agg, json_path)

    csv_df = pd.read_csv(csv_path)
    expected = pd.DataFrame({"symbol": ["BTC"], "confidence": [0.85], "score": [0.5]})
    pd.testing.assert_frame_equal(csv_df, expected)

    with open(json_path) as fh:
        data = json.load(fh)
    assert data == [{"symbol": "BTC", "confidence": 0.85, "score": 0.5}]

    scores = ri.run_analog_scoring(insp.dataframe, ["text"], query="a", top_k=1)
    assert scores[0][0] == 0
