from utils.enrichment.smc import run


def test_smc_run_features_and_vector():
    data = {"open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5}
    features, vector = run(data)

    expected_keys = {"range", "midpoint", "body", "is_bullish"}
    assert expected_keys <= features.keys()

    assert vector is not None
    assert len(vector) == 4
