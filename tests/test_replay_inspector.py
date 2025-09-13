import pandas as pd
import pytest

import replay_inspector as ri


def test_score_embedding_basic():
    emb = [1.0, 1.0]
    metrics = ri.score_embedding(emb)
    assert metrics["cosine_similarity"] == pytest.approx(1.0)
    assert metrics["cosine_distance"] == pytest.approx(0.0)


def test_score_embedding_zero_vector():
    emb = [0.0, 0.0, 0.0]
    metrics = ri.score_embedding(emb)
    assert metrics == {"cosine_similarity": 0.0, "cosine_distance": 1.0}


def test_aggregate_cosine_metrics():
    df = pd.DataFrame(
        {
            "symbol": ["BTC", "BTC"],
            "confidence": [0.9, 0.8],
            "embedding": [[1.0, 0.0], [0.0, 1.0]],
        }
    )

    # Bypass __init__ to provide the dataframe directly
    insp = ri.ReplayInspector.__new__(ri.ReplayInspector)
    insp._df = df

    agg = insp.aggregate(df)

    expected_sim = ri.score_embedding([1.0, 0.0])["cosine_similarity"]
    expected_dist = ri.score_embedding([1.0, 0.0])["cosine_distance"]

    expected = pd.DataFrame(
        {
            "symbol": ["BTC"],
            "confidence": [0.85],
            "cosine_similarity": [expected_sim],
            "cosine_distance": [expected_dist],
        }
    )

    pd.testing.assert_frame_equal(agg, expected)

