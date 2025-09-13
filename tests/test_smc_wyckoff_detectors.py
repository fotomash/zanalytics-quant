import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Optional

# Load only the class definitions needed for testing without executing
# the dashboard code that follows in the original module.
def load_analyzer():
    module_path = Path(__file__).resolve().parents[1] / "dashboard/_mix/5_  🧠 SMC & WYCKOFF.py"
    code = module_path.read_text(encoding="utf-8")
    start = code.index("class QRTQuantumAnalyzer")
    end = code.index("# =================== END QRT ANALYZER DEFINITIONS =====================")
    snippet = code[start:end]

    class QuantumMicrostructureAnalyzer:
        def __init__(self, config_path: str):
            self.config_path = config_path
            self.session_state = {}

    globals_dict = {
        "pd": pd,
        "np": np,
        "Dict": Dict,
        "Optional": Optional,
        "QuantumMicrostructureAnalyzer": QuantumMicrostructureAnalyzer,
    }
    # Execute the snippet using a single namespace so classes can reference
    # each other (e.g. ``TiquidityEngine`` used inside ``QRTQuantumAnalyzer``).
    exec(snippet, globals_dict, globals_dict)
    return globals_dict["QRTQuantumAnalyzer"]

Analyzer = load_analyzer()


def test_detect_selling_climax():
    analyzer = Analyzer("cfg")
    df = pd.DataFrame({
        "close": [100, 98, 97, 95, 90],
        "low": [99, 97, 96, 94, 89],
        "volume": [1000, 1100, 1200, 1300, 4000],
    })
    assert analyzer._detect_selling_climax(df)


def test_detect_accumulation_range():
    analyzer = Analyzer("cfg")
    df = pd.DataFrame({
        "high": [10, 12, 13, 14, 15] + [10.5] * 20,
        "low": [5, 6, 7, 8, 9] + [9.5] * 20,
        "volume": [1000] * 5 + [100] * 20,
    })
    assert analyzer._detect_accumulation_range(df)


def test_detect_spring():
    analyzer = Analyzer("cfg")
    df = pd.DataFrame({
        "low": [10, 9, 8, 7, 6, 4, 3, 8],
        "close": [10, 9, 8, 7, 6, 4, 5, 9],
    })
    assert analyzer._detect_spring(df) == 6


def test_detect_markup_beginning():
    analyzer = Analyzer("cfg")
    df = pd.DataFrame({
        "high": [10, 10.5, 10.8, 10.7, 10.9, 11.5],
        "close": [10, 10.3, 10.7, 10.6, 10.8, 11.6],
        "volume": [100, 120, 110, 115, 130, 300],
    })
    assert analyzer._detect_markup_beginning(df)
