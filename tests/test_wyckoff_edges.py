import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
import pytest
from components.wyckoff_adaptive import analyze_wyckoff_adaptive
from components.wyckoff_agents import MultiTFResolver

# Helper to create sample bar data
def _create_bars(n=200, price=1.0, vol=100.0, add_nans=False):
    idx = pd.to_datetime(pd.date_range("2025-01-01", periods=n, freq="T"))
    df = pd.DataFrame({
        "open": price, "high": price * 1.001, "low": price * 0.999,
        "close": price, "volume": float(vol)
    }, index=idx)
    if add_nans:
        df.loc[df.index[10:15], 'close'] = np.nan
        df.loc[df.index[20:25], 'volume'] = np.nan
    return df

def test_edge_flat_no_volume_dxy_style():
    """
    Edge Case 1: Flat, no-volume data (e.g., DXY) should never be misclassified as Distribution.
    It should default to Neutral or Accumulation/Markdown in a range.
    """
    df = _create_bars(vol=0) # Simulate no volume
    df['tick_volume'] = 1.0 # Use tick_volume fallback
    
    result = analyze_wyckoff_adaptive(df, win=50)
    labels = result["phases"]["labels"]
    
    # Assert that "Distribution" is not the dominant phase in a flat, quiet market
    assert "Distribution" not in list(labels[-50:])

def test_edge_news_spike_clamps_logits():
    """
    Edge Case 2: A sudden news spike should trigger the news buffer,
    activating the mask and clamping the analysis logits.
    """
    df = _create_bars()
    spike_time = df.index[100]
    
    # Inject a 3% price spike to simulate news
    df.loc[spike_time, 'high'] = df.loc[spike_time, 'close'] * 1.03
    df.loc[spike_time, 'close'] = df.loc[spike_time, 'close'] * 1.02
    df.loc[spike_time, 'volume'] = df.loc[spike_time, 'volume'] * 10
    
    # Analyze with the news buffer enabled
    result_with_buffer = analyze_wyckoff_adaptive(
        df, win=30, news_times=[spike_time], 
        news_cfg={"pre_bars": 1, "post_bars": 1, "volz_thresh": 2.0, "clamp": 0.5}
    )
    result_without_buffer = analyze_wyckoff_adaptive(df, win=30)
    
    news_mask = result_with_buffer["news_mask"]
    logits_clamped = result_with_buffer["phases"]["logits"]
    logits_unclamped = result_without_buffer["phases"]["logits"]

    assert news_mask.any(), "News mask should be active during the spike"
    # Verify that the max logit value during the news event is smaller with the buffer
    assert np.max(np.abs(logits_clamped[news_mask])) < np.max(np.abs(logits_unclamped[news_mask]))

def test_edge_mtf_resolver_flags_conflict():
    """
    Edge Case 3: The MTF resolver should correctly identify conflicts,
    e.g., when a lower timeframe shows Distribution during a higher timeframe Markup.
    """
    resolver = MultiTFResolver()
    
    # 1m labels showing Distribution
    labels_1m = np.array(["Markup", "Markup", "Distribution", "Distribution"])
    # 5m and 15m labels showing a clear Markup phase
    labels_5m = np.array(["Markup", "Markup", "Markup", "Markup"])
    labels_15m = np.array(["Markup", "Markup", "Markup", "Markup"])
    
    result = resolver.resolve(labels_1m, labels_5m, labels_15m)
    conflict_mask = result["conflict_mask"]
    
    assert conflict_mask.sum() == 2
    assert np.array_equal(conflict_mask, [False, False, True, True])

def test_edge_invalid_data_survives():
    """
    Edge Case 4: The analyzer should be resilient to NaN values in the input data
    and still produce an output of the correct shape without crashing.
    """
    df = _create_bars(add_nans=True)
    
    try:
        result = analyze_wyckoff_adaptive(df, win=50)
        # Check that outputs have the same length as the input dataframe
        assert len(result["phases"]["labels"]) == len(df)
        assert len(result["events"]["Spring"]) == len(df)
        assert not np.isnan(result["phases"]["logits"]).any()
    except Exception as e:
        pytest.fail(f"Analysis failed on data with NaNs: {e}")
