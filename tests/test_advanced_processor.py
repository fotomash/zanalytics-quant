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
