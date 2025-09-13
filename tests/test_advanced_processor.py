import importlib.util
import pathlib
import pytest
import numpy as np
import pandas as pd
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "advanced", pathlib.Path("utils/processors/advanced.py")
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)  # type: ignore
AdvancedProcessor = module.AdvancedProcessor


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
    processor = AdvancedProcessor(fractal_bars=1, fib_levels=[0.382, 0.618])
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
    processor = AdvancedProcessor(fractal_bars=1, fib_levels=[0.382, 0.618])
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
    processor = AdvancedProcessor(fractal_bars=1, fib_levels=[0.382, 0.618])
    result = processor.process(df, wave_only=True)
    assert result["elliott_wave"]["label"] is None
    assert result["elliott_wave"]["score"] == 0.0


def test_elliott_wave_bearish_impulse():
    df = pd.DataFrame(
        {
            "open": [10, 100, 90, 95, 80, 85, 70, 75, 60, 65, 50, 60], # Added 60 at end
            "high": [10, 100, 90, 95, 80, 85, 70, 75, 60, 65, 50, 60],
            "low": [8, 98, 88, 93, 78, 83, 68, 73, 58, 63, 48, 58],
            "close": [9, 99, 89, 94, 79, 84, 69, 74, 59, 64, 49, 59],
        }
    )
    processor = AdvancedProcessor(fractal_bars=1, fib_levels=[0.382, 0.618])
    result = processor.process(df)
    assert result["pivots"]["peaks"] == [1, 3, 5, 7, 9]
    assert result["pivots"]["troughs"] == [2, 4, 6, 8, 10]
    assert result["elliott_wave"]["label"] == "impulse_bearish"
    assert result["elliott_wave"]["score"] > 0.5


def test_elliott_wave_empty_dataframe():
    df = pd.DataFrame(
        columns=["open", "high", "low", "close"]
    )
    processor = AdvancedProcessor(fractal_bars=1, fib_levels=[0.382, 0.618])
    result = processor.process(df, wave_only=True)
    assert result == {}


def test_elliott_wave_llm_integration_mocked(sample_df):
    processor = AdvancedProcessor(fractal_bars=1, fib_levels=[0.382, 0.618])
    with patch.object(processor, '_llm_infer') as mock_llm_infer:
        mock_llm_infer.return_value = "Mocked LLM Forecast"
        result = processor.process(sample_df)
        
        assert mock_llm_infer.called
        assert "ewt_forecast" in result
        assert result["ewt_forecast"] == "Mocked LLM Forecast"
        assert result["elliott_wave"]["label"] == "impulse_bullish"


def test_elliott_wave_custom_fib_levels():
    df = pd.DataFrame(
        {
            "open": [20, 10, 20, 15, 25, 20, 30, 25, 35, 30, 40, 35],
            "high": [20, 10, 20, 15, 25, 20, 30, 25, 35, 30, 40, 35],
            "low": [18, 8, 15, 12, 18, 15, 22, 18, 28, 24, 32, 30],
            "close": [19, 9, 18, 13.5, 21.5, 17.5, 26, 21.5, 31.5, 27, 36, 32.5],
        }
    )
    # This df should produce a bullish impulse with ratios close to 0.5 and 0.7
    # Let's assume the ratios are 0.5 and 0.7 for simplicity
    custom_fib_levels = [0.5, 0.7]
    processor = AdvancedProcessor(fractal_bars=1, fib_levels=custom_fib_levels)

    # Manually get pivots, fractals, and gator to pass to elliott_wave
    # This is to isolate the fib_levels test
    pivots = processor.detect_pivots(df)
    fractals = {"up": [], "down": []} # No fractals
    gator = {"state": []} # No alligator state

    result = processor.elliott_wave(df, pivots, fractals, gator)
    
    assert result["label"] == "impulse_bullish"
    assert result["score"] == pytest.approx(0.75, abs=0.01)
