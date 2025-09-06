
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
import yaml


class RiskEnforcerV2:
    """Enhanced Risk Management System"""

    def __init__(self, config_path: str = "config/risk_config.yaml"):
        self.config = self._load_config(config_path)
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.positions: Dict[str, Dict] = {}
        self.correlation_matrix: Dict[str, float] = {}
        self.volatility_regime = "normal"
        self.max_daily_loss = self.config.get('max_daily_loss', 0.03)
        self.max_daily_trades = self.config.get('max_daily_trades', 5)
        self.max_position_size = self.config.get('max_position_size', 0.1)
        self.correlation_limit = self.config.get('correlation_limit', 0.95)
        self.kelly_fraction = self.config.get('kelly_fraction', 0.25)
        self.min_win_rate = self.config.get('min_win_rate', 0.55)
        logging.info("RiskEnforcerV2 initialized")

    def evaluate_trade_risk(self, signal: Dict, market_data: Dict) -> Dict:
        risk_assessment = {
            'allowed': True,
            'position_size': 0.0,
            'risk_factors': [],
            'warnings': [],
            'confidence_adjustment': 1.0,
        }
        if not self._check_daily_limits():
            risk_assessment['allowed'] = False
            risk_assessment['risk_factors'].append('daily_limits_exceeded')
            return risk_assessment
        correlation_risk = self._check_correlation_exposure(signal['symbol'])
        if correlation_risk['risk_level'] == 'high':
            risk_assessment['confidence_adjustment'] *= 0.5
            risk_assessment['warnings'].append('high_correlation_exposure')
        vol_adjustment = self._check_volatility_regime(market_data)
        risk_assessment['confidence_adjustment'] *= vol_adjustment
        position_size = self._calculate_kelly_position_size(signal, market_data)
        risk_assessment['position_size'] = position_size
        if self._detect_crisis_correlation(market_data):
            risk_assessment['confidence_adjustment'] *= 0.3
            risk_assessment['warnings'].append('crisis_correlation_detected')
        risk_assessment['risk_score'] = self._calculate_risk_score(signal, market_data)
        return risk_assessment

    def _check_daily_limits(self) -> bool:
        if abs(self.daily_pnl) >= self.max_daily_loss:
            logging.warning(f"Daily loss limit exceeded: {self.daily_pnl:.3f}")
            return False
        if self.daily_trades >= self.max_daily_trades:
            logging.warning(f"Daily trade limit exceeded: {self.daily_trades}")
            return False
        return True

    def _check_correlation_exposure(self, symbol: str) -> Dict:
        if not self.positions:
            return {'risk_level': 'low', 'max_correlation': 0.0, 'correlated_positions': []}
        max_correlation = 0.0
        correlated_positions = []
        for existing_symbol, position in self.positions.items():
            if existing_symbol == symbol:
                continue
            corr = self._get_correlation(symbol, existing_symbol)
            if abs(corr) > self.correlation_limit:
                max_correlation = max(max_correlation, abs(corr))
                correlated_positions.append({'symbol': existing_symbol, 'correlation': corr, 'position_size': position['size']})
        risk_level = 'high' if max_correlation > self.correlation_limit else 'medium' if max_correlation > 0.8 else 'low'
        return {'risk_level': risk_level, 'max_correlation': max_correlation, 'correlated_positions': correlated_positions}

    def _check_volatility_regime(self, market_data: Dict) -> float:
        current_vol = market_data.get('volatility', 0.02)
        historical_vol = market_data.get('historical_volatility', 0.02)
        vol_ratio = current_vol / historical_vol if historical_vol > 0 else 1.0
        if vol_ratio > 2.0:
            self.volatility_regime = "high"
            return 0.5
        elif vol_ratio > 1.5:
            self.volatility_regime = "elevated"
            return 0.75
        else:
            self.volatility_regime = "normal"
            return 1.0

    def _calculate_kelly_position_size(self, signal: Dict, market_data: Dict) -> float:
        win_probability = signal.get('confidence', 0.6)
        reward_risk_ratio = market_data.get('reward_risk_ratio', 2.0)
        loss_probability = 1 - win_probability
        if win_probability < self.min_win_rate:
            return 0.0
        kelly_fraction = (reward_risk_ratio * win_probability - loss_probability) / reward_risk_ratio
        kelly_fraction *= self.kelly_fraction
        kelly_fraction = min(kelly_fraction, self.max_position_size)
        kelly_fraction = max(kelly_fraction, 0.0)
        return kelly_fraction

    def _detect_crisis_correlation(self, market_data: Dict) -> bool:
        dxy_vix_correlation = market_data.get('correlation_dxy_vix', 0.0)
        if dxy_vix_correlation > 0.75:
            logging.warning(f"Crisis correlation detected: DXY-VIX = {dxy_vix_correlation:.3f}")
            return True
        return False

    def _calculate_risk_score(self, signal: Dict, market_data: Dict) -> float:
        risk_factors = []
        vol_risk = min(market_data.get('volatility', 0.02) / 0.05, 1.0)
        risk_factors.append(vol_risk)
        correlation_risk = self._check_correlation_exposure(signal['symbol'])
        risk_factors.append(correlation_risk['max_correlation'])
        if self._detect_crisis_correlation(market_data):
            risk_factors.append(0.9)
        confidence_risk = 1.0 - signal.get('confidence', 0.5)
        risk_factors.append(confidence_risk)
        return float(np.mean(risk_factors))

    def update_position(self, symbol: str, size: float, entry_price: float):
        self.positions[symbol] = {'size': size, 'entry_price': entry_price, 'timestamp': datetime.now()}
        self.daily_trades += 1

    def update_pnl(self, pnl: float):
        self.daily_pnl += pnl

    def reset_daily_limits(self):
        self.daily_pnl = 0.0
        self.daily_trades = 0
        logging.info("Daily risk limits reset")

    def _get_correlation(self, symbol1: str, symbol2: str) -> float:
        pair = f"{symbol1}_{symbol2}"
        reverse_pair = f"{symbol2}_{symbol1}"
        return self.correlation_matrix.get(pair, self.correlation_matrix.get(reverse_pair, 0.0))

    def update_correlation_matrix(self, correlation_data: Dict):
        self.correlation_matrix.update(correlation_data)

    def _load_config(self, config_path: str) -> Dict:
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            return {}


class KellyCalculator:
    """Standalone Kelly Criterion calculator"""

    @staticmethod
    def calculate_kelly_fraction(win_rate: float, avg_win: float, avg_loss: float) -> float:
        if avg_loss <= 0:
            return 0.0
        reward_risk_ratio = avg_win / avg_loss
        loss_rate = 1 - win_rate
        kelly_fraction = (reward_risk_ratio * win_rate - loss_rate) / reward_risk_ratio
        return max(kelly_fraction, 0.0)

    @staticmethod
    def calculate_optimal_position_size(portfolio_value: float, kelly_fraction: float,
                                       max_risk_per_trade: float = 0.02,
                                       kelly_scaling: float = 0.25) -> float:
        scaled_kelly = kelly_fraction * kelly_scaling
        risk_adjusted = min(scaled_kelly, max_risk_per_trade)
        return portfolio_value * risk_adjusted


if __name__ == "__main__":
    risk_enforcer = RiskEnforcerV2()
    signal = {'symbol': 'BTC', 'signal': 'BUY', 'confidence': 0.75}
    market_data = {'volatility': 0.03, 'historical_volatility': 0.025,
                   'correlation_dxy_vix': 0.83, 'reward_risk_ratio': 2.5}
    print(risk_enforcer.evaluate_trade_risk(signal, market_data))
