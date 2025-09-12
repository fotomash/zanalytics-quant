import importlib.util
import pathlib

import pandas as pd
import msgpack

from utils import streaming

spec = importlib.util.spec_from_file_location(
    "advanced", pathlib.Path("utils/processors/advanced.py")
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)  # type: ignore
AdvancedProcessor = module.AdvancedProcessor


def _sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open": [5, 7, 9, 7, 5],
            "high": [5, 7, 9, 7, 5],
            "low": [5, 3, 1, 3, 5],
            "close": [5, 7, 9, 7, 5],
        }
    )


def test_fractals_only_msgpack_payload_size():
    df = _sample_df()
    processor = AdvancedProcessor(fractal_bars=2)
    result = processor.process(df, fractals_only=True)
    assert set(result.keys()) == {"fractals"}
    packed = streaming.serialize(result)
    unpacked = msgpack.unpackb(packed, raw=False)
    assert unpacked == result
    # payload should be smaller than a full analysis
    full = streaming.serialize(processor.process(df))
    assert len(packed) < len(full)
    assert len(packed) < 200


def test_wave_only_msgpack_payload_size():
    df = _sample_df()
    processor = AdvancedProcessor(fractal_bars=2)
    result = processor.process(df, wave_only=True)
    assert set(result.keys()) == {"elliott_wave"}
    packed = streaming.serialize(result)
    unpacked = msgpack.unpackb(packed, raw=False)
    assert unpacked == result
    full = streaming.serialize(processor.process(df))
    assert len(packed) < len(full)
    assert len(packed) < 200
