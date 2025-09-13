import numpy as np
import pandas as pd

from utils.enrichment.rsi import RSIProcessor, process


def test_rsi_processor_matches_expected_values():
    prices = [
        44.34,
        44.09,
        44.15,
        43.61,
        44.33,
        44.83,
        45.10,
        45.42,
        45.84,
        46.08,
        45.89,
        46.03,
        45.61,
        46.28,
        46.28,
        46.00,
        46.03,
        46.41,
        46.22,
        45.64,
    ]
    df = pd.DataFrame({"close": prices})
    processor = RSIProcessor(period=14)
    enriched, vector = processor.enrich(df, return_vector=True)

    # Expected RSI values for the final three rows calculated independently
    expected_tail = np.array([80.567686, 73.333333, 59.806295])
    assert np.allclose(enriched["rsi_14"].iloc[-3:].values, expected_tail, rtol=1e-6)

    # Vector output should mirror the RSI column
    assert isinstance(vector, np.ndarray)
    assert np.allclose(vector, enriched["rsi_14"].to_numpy(), equal_nan=True)


def test_rsi_processor_without_vector():
    df = pd.DataFrame({"close": np.linspace(1, 30, 30)})
    enriched, vector = RSIProcessor().enrich(df)
    assert vector is None
    assert "rsi_14" in enriched.columns


def test_rsi_process_wrapper():
    df = pd.DataFrame({"close": np.linspace(1, 30, 30)})
    result, vector = process(df, return_vector=True)
    enriched = result["df"]
    assert "rsi_14" in enriched.columns
    assert isinstance(vector, np.ndarray)
    assert np.allclose(vector, enriched["rsi_14"].to_numpy(), equal_nan=True)

    result_no_vec, vector_none = process(df)
    assert vector_none is None
    assert "rsi_14" in result_no_vec["df"].columns
