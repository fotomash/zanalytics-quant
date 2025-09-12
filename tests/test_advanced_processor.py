import importlib.util
import pathlib

import numpy as np
import pandas as pd

spec = importlib.util.spec_from_file_location(
    "advanced", pathlib.Path("utils/processors/advanced.py")
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)  # type: ignore
AdvancedProcessor = module.AdvancedProcessor


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


def test_zigzag_and_elliott_wave():
    df = pd.DataFrame(
        {
            "open": [20, 10, 20, 15, 25, 20, 30, 25, 35, 30, 40, 35],
            "high": [20, 10, 20, 15, 25, 20, 30, 25, 35, 30, 40, 35],
            "low": [18, 8, 15, 12, 18, 15, 22, 18, 28, 24, 32, 30],
            "close": [19, 9, 18, 13.5, 21.5, 17.5, 26, 21.5, 31.5, 27, 36, 32.5],
        }
    )
    processor = AdvancedProcessor(fractal_bars=1)
    result = processor.process(df)
    assert result["pivots"]["peaks"] == [2, 4, 6, 8, 10]
    assert result["pivots"]["troughs"] == [1, 3, 5, 7, 9]
    assert result["elliott_wave"]["label"] == "impulse_bullish"
    assert result["elliott_wave"]["score"] > 0.5
    assert "ewt_forecast" in result
    assert isinstance(result["ewt_forecast"], str)
