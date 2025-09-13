import ast
from pathlib import Path
import pandas as pd
import numpy as np
from typing import Dict, Optional


def load_analyzer():
    """Extract QRTQuantumAnalyzer class without executing dashboard code."""
    root = Path(__file__).resolve().parents[1]
    path = root / "dashboard" / "_mix" / "5_  🧠 SMC & WYCKOFF.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    class_node = next(
        node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "QRTQuantumAnalyzer"
    )
    module = ast.Module(body=[class_node], type_ignores=[])
    code = compile(module, str(path), "exec")
    class QuantumMicrostructureAnalyzer:
        def __init__(self, config_path=None):
            pass

    namespace = {
        "pd": pd,
        "np": np,
        "Dict": Dict,
        "Optional": Optional,
        "QuantumMicrostructureAnalyzer": QuantumMicrostructureAnalyzer,
        "TiquidityEngine": type("TiquidityEngine", (), {}),
        "WyckoffQuantumAnalyzer": type("WyckoffQuantumAnalyzer", (), {}),
    }
    exec(code, namespace)
    return namespace["QRTQuantumAnalyzer"]


QRTAnalyzer = load_analyzer()


def test_detect_selling_climax():
    analyzer = QRTAnalyzer(None)
    df = pd.DataFrame({
        "close": [10, 9.5, 9.0, 8.5, 7.0],
        "low": [9.8, 9.3, 8.8, 8.0, 6.8],
        "high": [10.2, 9.7, 9.3, 9.0, 7.5],
        "volume": [100, 110, 120, 130, 400]
    })
    assert analyzer._detect_selling_climax(df)


def test_detect_accumulation_range():
    analyzer = QRTAnalyzer(None)
    trend_prices = pd.Series(np.linspace(30, 20, 10))
    prices1 = pd.Series([10, 9, 8, 7, 6, 5, 4, 3, 2, 1])
    prices2 = pd.Series([1.1, 1.2, 1.15, 1.18, 1.12, 1.14, 1.13, 1.16, 1.15, 1.17])
    df = pd.DataFrame({
        "close": pd.concat([trend_prices, prices1, prices2], ignore_index=True),
        "high": pd.concat([trend_prices + 0.2, prices1 + 0.2, prices2 + 0.1], ignore_index=True),
        "low": pd.concat([trend_prices - 0.2, prices1 - 0.2, prices2 - 0.1], ignore_index=True),
        "volume": [300]*10 + [200]*10 + [50]*10
    })
    assert analyzer._detect_accumulation_range(df)


def test_detect_spring():
    analyzer = QRTAnalyzer(None)
    df = pd.DataFrame({
        "close": [10, 10.1, 10.2, 10.15, 10.0],
        "high": [10.2, 10.3, 10.25, 10.2, 10.1],
        "low": [9.8, 9.9, 9.85, 9.8, 9.4]
    })
    spring_idx = analyzer._detect_spring(df)
    assert spring_idx == len(df) - 1


def test_detect_markup_beginning():
    analyzer = QRTAnalyzer(None)
    df = pd.DataFrame({
        "close": [10, 10.1, 10.2, 10.15, 10.5],
        "high": [10.2, 10.3, 10.25, 10.2, 10.6],
        "low": [9.9, 10.0, 10.1, 9.95, 10.3],
        "volume": [100, 100, 100, 100, 300]
    })
    assert analyzer._detect_markup_beginning(df)
