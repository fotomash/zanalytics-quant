import pandas as pd

from utils.enrichment import poi


def test_run_basic():
    df = pd.DataFrame({"high": [1.0, 2.0, 3.0], "low": [0.5, 1.0, 2.0]})
    enriched, vector = poi.run(df)
    assert enriched == {"support": 0.5, "resistance": 3.0, "midpoint": 1.75}
    assert vector == [0.5, 3.0, 1.75]


def test_run_empty():
    enriched, vector = poi.run(pd.DataFrame())
    assert enriched == {}
    assert vector == []


def test_run_missing_columns():
    df = pd.DataFrame({"open": [1, 2, 3]})
    enriched, vector = poi.run(df)
    assert enriched == {}
    assert vector == []


def test_run_none():
    enriched, vector = poi.run(None)
    assert enriched == {}
    assert vector == []
