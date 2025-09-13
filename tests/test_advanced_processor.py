import importlib.util
import pathlib
import pytest
import numpy as np
import pandas as pd
from unittest.mock import patch

from core.harmonic_processor import HarmonicProcessor

spec = importlib.util.spec_from_file_location(
    "advanced", pathlib.Path("utils/processors/advanced.py")
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)  # type: ignore
AdvancedProcessor = module.AdvancedProcessor


def detect_harmonic_patterns(df: pd.DataFrame) -> dict:
    """Convenience wrapper for harmonic pattern analysis."""
    result = HarmonicProcessor().analyze(df)
    harmonic = result.get("harmonic")
    if hasattr(harmonic, "model_dump"):
        return harmonic.model_dump()
    return harmonic


def _generate_abcd_dataframe(bullish: bool = True) -> pd.DataFrame:
    """Create a synthetic ABCD harmonic pattern.

    The pattern ratios are chosen to satisfy the simplified checker in
    :class:`core.harmonic_processor.HarmonicPatternDetector`.  Extra leading
    and trailing bars ensure the internal pivot finder can locate all five
    required turning points.
    """

    xa = 1.0
    ab = 3.33
    bc = 0.618 * ab
    cd = 0.618 * bc

    if bullish:
        x = 0.0
        a = x - xa
        b = a + ab
        c = b - bc
        d = c + cd
        pre = [-0.5, -0.4, -0.3, -0.2, -0.1]
        post = [d - 0.5]
    else:
        x = 0.0
        a = x + xa
        b = a - ab
        c = b + bc
        d = c - cd
        pre = [0.5, 0.4, 0.3, 0.2, 0.1]
        post = [d + 0.5]

    prices = [*pre, x, a, b, c, d, *post]
    data: list[float] = []
    for start, end in zip(prices, prices[1:]):
        steps = np.linspace(start, end, 6, endpoint=False)
        data.extend(steps.tolist())
    data.append(prices[-1])
    arr = np.array(data)
    return pd.DataFrame({"open": arr, "high": arr, "low": arr, "close": arr})


@pytest.fixture
def sample_df():
    """A sample DataFrame for testing."""
    return pd.DataFrame(
        {
            "open": [20, 10, 20, 15, 25, 20, 30, 25, 35, 30, 40, 35],
            "high": [20, 10, 20, 15, 25, 20, 30, 25, 35, 30, 40, 35],
            "low": [18, 8, 15, 12, 18, 15, 22, 18, 28, 24, 32, 30],
            "close": [19, 9, 18, 13.5, 21.5, 17.5, 26, 21.5, 31.5, 27, 36, 32.5],
        }
    )


def test_vectorized_fractals():
    df = pd.DataFrame(
        {
            "open": [5, 7, 9, 7, 5],
            "high": [5, 7, 9, 7, 5],
            "low": [5, 3, 1, 3, 5],
            "close": [5, 7, 9, 7, 5],
        }
    )
    processor = AdvancedProcessor(fractal_bars=2)
    fractals = processor.detect_fractals(df)
    assert fractals["up"] == [2]
    assert fractals["down"] == [2]


def test_alligator_state_bullish():
    close = np.linspace(1, 10, 50)
    df = pd.DataFrame(
        {
            "open": close,
            "high": close + 0.1,
            "low": close - 0.1,
            "close": close,
        }
    )
    processor = AdvancedProcessor()
    result = processor.process(df)
    assert result["alligator"]["state"][-1] == "bullish"


def test_elliott_wave_bullish_impulse(sample_df):
    processor = AdvancedProcessor(fractal_bars=1)
    result = processor.process(sample_df)
    assert result["pivots"]["peaks"] == [2, 4, 6, 8, 10]
    assert result["pivots"]["troughs"] == [1, 3, 5, 7, 9]
    assert result["elliott_wave"]["label"] == "impulse_bullish"
    assert result["elliott_wave"]["score"] > 0.5
    assert "ewt_forecast" in result
    assert isinstance(result["ewt_forecast"], str)


def test_elliott_wave_less_than_5_points():
    df = pd.DataFrame(
        {
            "open": [10, 20, 15, 25],
            "high": [10, 20, 15, 25],
            "low": [8, 15, 12, 18],
            "close": [9, 18, 13.5, 21.5],
        }
    )
    processor = AdvancedProcessor(fractal_bars=1)
    result = processor.process(df, wave_only=True)
    assert result["elliott_wave"]["label"] is None
    assert result["elliott_wave"]["score"] == 0.0


def test_elliott_wave_consecutive_same_type_pivots():
    df = pd.DataFrame(
        {
            "open": [10, 20, 30, 30, 20, 10, 5],
            "high": [10, 20, 30, 30, 20, 10, 5],
            "low": [8, 18, 28, 28, 18, 8, 3],
            "close": [9, 19, 29, 29, 19, 9, 4],
        }
    )
    processor = AdvancedProcessor(fractal_bars=1)
    result = processor.process(df, wave_only=True)
    assert result["elliott_wave"]["label"] is None
    assert result["elliott_wave"]["score"] == 0.0


def test_elliott_wave_bearish_impulse():
    df = pd.DataFrame(
        {
            "open": [50, 40, 45, 35, 40, 30, 35, 25, 30, 20, 25, 15, 20, 10],
            "high": [50, 40, 45, 35, 40, 30, 35, 25, 30, 20, 25, 15, 20, 10],
            "low": [48, 38, 43, 33, 38, 28, 33, 23, 28, 18, 23, 13, 18, 8],
            "close": [49, 39, 44, 34, 39, 29, 34, 24, 29, 19, 24, 14, 19, 9],
        }
    )
    processor = AdvancedProcessor(fractal_bars=1)
    result = processor.process(df)
    assert result["pivots"]["peaks"] == [0, 2, 4, 6, 8, 10, 12]
    assert result["pivots"]["troughs"] == [1, 3, 5, 7, 9, 11, 13]
    assert result["elliott_wave"]["label"] == "impulse_bearish"
    assert result["elliott_wave"]["score"] > 0.5


def test_elliott_wave_empty_dataframe():
    df = pd.DataFrame(columns=["open", "high", "low", "close"])
    processor = AdvancedProcessor(fractal_bars=1)
    result = processor.process(df, wave_only=True)
    assert result == {}


@patch("utils.processors.advanced.AdvancedProcessor._llm_infer")
def test_elliott_wave_llm_integration_mocked(mock_llm_infer, sample_df):
    mock_llm_infer.return_value = "Mocked LLM Forecast"
    processor = AdvancedProcessor(fractal_bars=1)
    result = processor.process(sample_df)

    assert mock_llm_infer.called
    assert "ewt_forecast" in result
    assert result["ewt_forecast"] == "Mocked LLM Forecast"
    assert (
        result["elliott_wave"]["label"] == "impulse_bullish"
    )  # Ensure elliott wave still processed


def test_detect_harmonic_patterns_bullish():
    df = _generate_abcd_dataframe(bullish=True)
    result = detect_harmonic_patterns(df)
    patterns = result["harmonic_patterns"]
    assert patterns and patterns[0]["pattern"] == "ABCD"
    prz = patterns[0]["prz"]
    assert pytest.approx(prz["low"], rel=1e-3) == -1.0
    assert pytest.approx(prz["high"], rel=1e-3) == 2.33
    assert patterns[0]["confidence"] > 0


def test_detect_harmonic_patterns_bearish():
    df = _generate_abcd_dataframe(bullish=False)
    result = detect_harmonic_patterns(df)
    patterns = result["harmonic_patterns"]
    assert patterns and patterns[0]["pattern"] == "ABCD"
    prz = patterns[0]["prz"]
    assert pytest.approx(prz["low"], rel=1e-3) == -2.33
    assert pytest.approx(prz["high"], rel=1e-3) == 1.0
    assert patterns[0]["confidence"] > 0


def test_detect_harmonic_patterns_none():
    close = np.linspace(1, 50, 60)
    df = pd.DataFrame({"open": close, "high": close, "low": close, "close": close})
    result = detect_harmonic_patterns(df)
    assert result["harmonic_patterns"] == []
