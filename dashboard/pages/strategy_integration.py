#!/usr/bin/env python3
"""
ZANFLOW Strategy Integration
Connect trading strategies to API
"""

import json
import redis
import requests
from abc import ABC, abstractmethod
from datetime import datetime
import pandas as pd
import numpy as np

class BaseStrategy(ABC):
    """Base class for all trading strategies"""

    def __init__(self, symbol, api_url="http://localhost:8080"):
        self.symbol = symbol
        self.api_url = api_url
        self.redis = redis.Redis(host='localhost', port=6379, decode_responses=True)
        self.position = None
        self.signals = []

    @abstractmethod
    def calculate_signal(self, data):
        """Calculate trading signal from data"""
        pass

    def get_latest_data(self):
        """Get latest symbol data"""
        try:
            response = requests.get(f"{self.api_url}/data/{self.symbol}")
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return None

    def run(self):
        """Run strategy on latest data"""
        data = self.get_latest_data()
        if data:
            signal = self.calculate_signal(data)
            if signal:
                self.execute_signal(signal)
                self.store_signal(signal)

    def execute_signal(self, signal):
        """Execute trading signal"""
        # This would connect to your broker API
        print(f"Signal: {signal}")

    def store_signal(self, signal):
        """Store signal in Redis"""
        signal_data = {
            'strategy': self.__class__.__name__,
            'symbol': self.symbol,
            'signal': signal,
            'timestamp': datetime.now().isoformat()
        }

        # Store in Redis
        self.redis.lpush(f"signals:{self.symbol}", json.dumps(signal_data))
        self.redis.publish(f"signals:{self.symbol}", json.dumps(signal_data))

class RSIMomentumStrategy(BaseStrategy):
    """RSI + Momentum Strategy"""

    def calculate_signal(self, data):
        if 'enriched' not in data:
            return None

        enriched = data['enriched']
        rsi = enriched.get('rsi', 50)
        momentum = enriched.get('momentum', 0)
        trend = enriched.get('trend', 'NEUTRAL')

        # Buy signal
        if rsi < 30 and momentum > 0 and trend == 'UPTREND':
            return {
                'action': 'BUY',
                'reason': f'RSI oversold ({rsi:.1f}) + positive momentum',
                'strength': 'STRONG'
            }

        # Sell signal  
        elif rsi > 70 and momentum < 0 and trend == 'DOWNTREND':
            return {
                'action': 'SELL',
                'reason': f'RSI overbought ({rsi:.1f}) + negative momentum',
                'strength': 'STRONG'
            }

        return None

class VolumeBreakoutStrategy(BaseStrategy):
    """Volume-based breakout strategy"""

    def calculate_signal(self, data):
        volume = data.get('volume', {})
        enriched = data.get('enriched', {})

        # Check volume spike
        current_vol = volume.get('per_minute', 0)
        avg_vol = volume.get('last_5min', 0)

        if avg_vol > 0:
            vol_ratio = current_vol / avg_vol

            # Volume spike detected
            if vol_ratio > 2.0:  # 200% of average
                trend = enriched.get('trend', 'NEUTRAL')

                if trend == 'UPTREND':
                    return {
                        'action': 'BUY',
                        'reason': f'Volume spike ({vol_ratio:.1f}x) in uptrend',
                        'strength': 'MEDIUM'
                    }
                elif trend == 'DOWNTREND':
                    return {
                        'action': 'SELL', 
                        'reason': f'Volume spike ({vol_ratio:.1f}x) in downtrend',
                        'strength': 'MEDIUM'
                    }

        return None

class ScalpingStrategy(BaseStrategy):
    """Fast scalping based on volatility"""

    def __init__(self, symbol, api_url="http://localhost:8080"):
        super().__init__(symbol, api_url)
        self.last_signal_time = None

    def calculate_signal(self, data):
        enriched = data.get('enriched', {})

        # Check volatility
        vol_1min = enriched.get('volatility_1min', 0)
        vol_5min = enriched.get('volatility_5min', 0)

        # High short-term volatility vs longer term
        if vol_1min > vol_5min * 1.5:
            rsi = enriched.get('rsi', 50)

            # Quick reversal trades
            if rsi < 20:
                return {
                    'action': 'BUY',
                    'reason': 'Extreme oversold in high volatility',
                    'strength': 'SCALP',
                    'target_pips': 5,
                    'stop_pips': 3
                }
            elif rsi > 80:
                return {
                    'action': 'SELL',
                    'reason': 'Extreme overbought in high volatility',
                    'strength': 'SCALP',
                    'target_pips': 5,
                    'stop_pips': 3
                }

        return None

# Strategy Manager
class StrategyManager:
    """Manage multiple strategies"""

    def __init__(self):
        self.strategies = []
        self.redis = redis.Redis(host='localhost', port=6379, decode_responses=True)

    def add_strategy(self, strategy):
        """Add strategy to manager"""
        self.strategies.append(strategy)

    def run_all(self):
        """Run all strategies"""
        for strategy in self.strategies:
            try:
                strategy.run()
            except Exception as e:
                print(f"Error in {strategy.__class__.__name__}: {e}")

    def get_all_signals(self, symbol=None):
        """Get all recent signals"""
        if symbol:
            signals = self.redis.lrange(f"signals:{symbol}", 0, 99)
        else:
            all_signals = []
            for key in self.redis.keys("signals:*"):
                signals = self.redis.lrange(key, 0, 9)
                all_signals.extend(signals)
            signals = all_signals

        return [json.loads(s) for s in signals]

    def clear_old_signals(self, hours=24):
        """Clear signals older than X hours"""
        cutoff = datetime.now() - timedelta(hours=hours)

        for key in self.redis.keys("signals:*"):
            signals = self.redis.lrange(key, 0, -1)
            self.redis.delete(key)

            for signal in signals:
                sig_data = json.loads(signal)
                sig_time = datetime.fromisoformat(sig_data['timestamp'])
                if sig_time > cutoff:
                    self.redis.rpush(key, signal)

# Example usage
if __name__ == "__main__":
    # Create strategy manager
    manager = StrategyManager()

    # Add strategies for different symbols
    manager.add_strategy(RSIMomentumStrategy("EURUSD"))
    manager.add_strategy(VolumeBreakoutStrategy("EURUSD"))
    manager.add_strategy(ScalpingStrategy("GBPUSD"))

    # Run strategies
    import time
    while True:
        manager.run_all()

        # Get recent signals
        signals = manager.get_all_signals()
        for signal in signals[-5:]:  # Last 5 signals
            print(f"{signal['timestamp']}: {signal['symbol']} - {signal['signal']}")

        time.sleep(1)  # Run every second
