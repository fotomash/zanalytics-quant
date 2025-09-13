import pandas as pd

from scripts import replay_inspector as ri


def test_analog_scores_order():
    embeddings = [[1, 0], [0, 1], [1, 1]]
    query = [1, 0]
    result = ri.analog_scores(embeddings, query, top_k=2)
    assert result[0][0] == 0
    assert result[0][1] >= result[1][1]


def test_run_analog_scoring_with_monkeypatched_embed(monkeypatch):
    # simple deterministic embed: length of text as first dimension
    def fake_embed(text: str):
        return [float(len(text)), 0.0]

    monkeypatch.setattr(ri, "embed", fake_embed)

    df = pd.DataFrame({"text": ["a", "abcd"]})
    scores = ri.run_analog_scoring(df, ["text"], query="a", top_k=1)
    assert scores[0][0] == 0
