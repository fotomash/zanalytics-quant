from risk_management.risk_enforcer_v2 import RiskEnforcerV2, KellyCalculator


def test_evaluate_trade_risk():
    enforcer = RiskEnforcerV2()
    signal = {'symbol': 'BTC', 'confidence': 0.8}
    market = {'volatility': 0.03, 'historical_volatility': 0.02, 'reward_risk_ratio': 2.0}
    result = enforcer.evaluate_trade_risk(signal, market)
    assert 'risk_score' in result
    assert result['allowed'] is True


def test_kelly_calculator():
    fraction = KellyCalculator.calculate_kelly_fraction(0.6, 2, 1)
    size = KellyCalculator.calculate_optimal_position_size(1000, fraction)
    assert size >= 0
