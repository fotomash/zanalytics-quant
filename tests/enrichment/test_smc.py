from utils.enrichment import smc_process  # package-level export


def test_smc_process_features_and_vector():
    data = {"open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5}
    features, vector = smc_process(data)

    expected_keys = {"range", "midpoint", "body", "is_bullish"}
    assert expected_keys <= features.keys()

    assert vector is not None
    assert len(vector) == 4
