import numpy as np
import pandas as pd

from utils import tick_enricher


def test_enrich_ticks_respects_stream_config(tmp_path, monkeypatch):
    df = pd.DataFrame(
        {
            "open": [1, 2, 3],
            "high": [1, 2, 3],
            "low": [1, 2, 3],
            "close": [1, 2, 3],
            "volume": [100, 100, 100],
        }
    )

    class StubEngine:
        def calculate_all_indicators(self, _df):
            return {
                "RSI_14": np.array([30, 40, 50]),
                "MACD_12_26_9": np.array([0.1, 0.2, 0.3]),
                "MACD_SIGNAL_12_26_9": np.array([0.05, 0.1, 0.15]),
                "MACD_HIST_12_26_9": np.array([0.05, 0.1, 0.15]),
                "BB_UPPER_20": np.array([1, 2, 3]),
                "BB_MIDDLE_20": np.array([0.5, 1.5, 2.5]),
                "BB_LOWER_20": np.array([0, 1, 2]),
            }

    monkeypatch.setattr(tick_enricher, "_get_indicator_engine", lambda: StubEngine())

    stream_dir = tmp_path / "streams"
    stream_dir.mkdir()
    (stream_dir / "EURUSD.yaml").write_text("indicators:\n  rsi: true\n  macd: true\n")

    result = tick_enricher.enrich_ticks(df, "EURUSD", stream_cfg_dir=stream_dir)
    indicators = result["indicators"]

    assert indicators["rsi"] == 50.0
    assert "macd" in indicators and indicators["macd"] == 0.3
    assert "bb_upper" not in indicators
