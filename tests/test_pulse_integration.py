import pytest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pulse_kernel import PulseKernel
from core.predictive_scorer import PredictiveScorer
from risk_enforcer import RiskEnforcer
from datetime import datetime


@pytest.fixture
def sample_market_data():
    """Fixture for test market data"""
    return {
        'symbol': 'EURUSD',
        'timeframe': 'H1',
        'timestamp': datetime.now(),
        'open': 1.0850,
        'high': 1.0875,
        'low': 1.0845,
        'close': 1.0865,
        'volume': 1250,
        'atr': 0.0015,
        'rsi': 58,
        'macd': 0.0003,
        'macd_signal': 0.0002,
        'ema_20': 1.0855,
        'ema_50': 1.0845,
        'trend': 'up'
    }


@pytest.mark.integration
def test_confluence_scorer(sample_market_data):
    """Test predictive scoring"""
    scorer = PredictiveScorer("pulse_config.yaml")
    result = scorer.score(sample_market_data)

    assert 'maturity_score' in result
    assert 0 <= result['maturity_score'] <= 100
    assert 'grade' in result


@pytest.mark.integration
def test_risk_enforcer():
    """Test risk enforcement"""
    enforcer = RiskEnforcer()

    # Test with safe conditions
    safe_signal = {
        'confluence_score': 75,
        'session_stats': {
            'trades_today': 2,
            'daily_pnl': -0.01,
            'confidence_level': 0.5
        },
        'market_data': {}
    }

    decision = enforcer.evaluate_signal(safe_signal)
    assert 'approved' in decision
    assert 'reason' in decision
    assert 'risk_score' in decision


@pytest.mark.integration
def test_daily_loss_limit():
    """Test daily loss limit protection"""
    enforcer = RiskEnforcer()

    # Test with excessive loss
    risky_signal = {
        'confluence_score': 80,
        'session_stats': {
            'trades_today': 2,
            'daily_pnl': -0.035,  # Exceeds 3% limit
            'confidence_level': 0.5
        },
        'market_data': {}
    }

    # Simulate daily loss exceeding limit
    enforcer.daily_stats['total_pnl'] = -enforcer.limits['daily_loss_limit'] - 1

    decision = enforcer.evaluate_signal(risky_signal)
    assert decision['approved'] is False
    assert 'DAILY_LIMIT_REACHED' in decision['flags']


@pytest.mark.integration
def test_overconfidence_protection():
    """Test overconfidence detection"""
    enforcer = RiskEnforcer()
    enforcer.state['consecutive_wins'] = 4
    enforcer.state['confidence_level'] = 0.9

    signal = {
        'confluence_score': 85,
        'session_stats': {'confidence_level': 0.9},
        'market_data': {}
    }

    decision = enforcer.evaluate_signal(signal)
    assert 'OVERCONFIDENCE_ALERT' in decision.get('flags', [])

# Run with: pytest tests/test_pulse_integration.py -v
