import pandas as pd
from pulse_kernel import PulseKernel


def _dummy_df(n=10):
    idx = pd.date_range('2025-01-01', periods=n, freq='T')
    data = {
        'open': [1.0] * n,
        'high': [1.001] * n,
        'low': [0.999] * n,
        'close': [1.0] * n,
        'volume': [100] * n,
    }
    return pd.DataFrame(data, index=idx)


def test_full_pipeline_allows_when_rules_locked():
    kernel = PulseKernel()
    kernel.risk.lock_rules()
    kernel.journal.log = lambda entry: None  # avoid filesystem writes
    df = _dummy_df()
    result = kernel.process(df)
    assert 'score' in result
    assert result['allowed'] is True
