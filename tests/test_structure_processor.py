import importlib.util
import pathlib
import pandas as pd
import numpy as np

spec = importlib.util.spec_from_file_location(
    "structure", pathlib.Path("utils/processors/structure.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)  # type: ignore
StructureProcessor = module.StructureProcessor


def test_identify_fair_value_gaps():
    df = pd.DataFrame({
        'open': [100, 101, 102, 103, 110],
        'high': [101, 102, 103, 104, 111],
        'low': [99, 100, 101, 102, 109],
        'close': [100.5, 101.5, 102.5, 103.5, 110.5],
    })
    processor = StructureProcessor()
    gaps = processor.identify_fair_value_gaps(df)
    assert any(g['type'] == 'bullish_fvg' for g in gaps)


def test_wyckoff_markup_detection():
    base = [100 + 0.05 * np.sin(i / 3) for i in range(60)]
    markup = list(np.linspace(100.5, 110, 20))
    prices = base + markup
    df = pd.DataFrame({
        'open': prices,
        'high': [p + 0.1 for p in prices],
        'low': [p - 0.1 for p in prices],
        'close': prices,
        'volume': [100] * 60 + [300] * 20,
    })
    processor = StructureProcessor()
    result = processor.analyze_wyckoff(df)
    assert any(p['phase'] == 'markup' for p in result['phases'])
