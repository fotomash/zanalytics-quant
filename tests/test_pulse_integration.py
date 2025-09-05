import pandas as pd
import pytest
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from pulse_kernel import PulseKernel, JournalEngine


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


@pytest.mark.integration
def test_full_pipeline_allows_when_rules_locked(tmp_path):
    journal = JournalEngine(path=tmp_path / "journal.json")
    kernel = PulseKernel(journal=journal)
    kernel.journal.log = lambda entry: None
    kernel.risk.lock_rules()
    df = _dummy_df()
    result = kernel.process(df)
    assert "score" in result
    assert result["allowed"] is True
