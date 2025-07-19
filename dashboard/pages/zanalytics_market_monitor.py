"""
ZAnalytics Real-time Market Monitor
Monitors market conditions and generates alerts based on:
- Price movements
- Volume anomalies
- Technical indicator signals
- Pattern completions
- Risk thresholds
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
import json
import asyncio
from dataclasses import dataclass
from enum import Enum
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AlertType(Enum):
    """Types of market alerts"""
    PRICE_BREAKOUT = "price_breakout"
    VOLUME_SPIKE = "volume_spike"
    PATTERN_COMPLETE = "pattern_complete"
    INDICATOR_SIGNAL = "indicator_signal"
    RISK_THRESHOLD = "risk_threshold"
    REGIME_CHANGE = "regime_change"
    CORRELATION_ALERT = "correlation_alert"
    VOLATILITY_ALERT = "volatility_alert"

class AlertPriority(Enum):
    """Alert priority levels"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class MarketAlert:
    """Market alert data structure"""
    alert_id: str
    timestamp: datetime
    symbol: str
    alert_type: AlertType
    priority: AlertPriority
    title: str
    description: str
    data: Dict[str, Any]
    action_required: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            'alert_id': self.alert_id,
            'timestamp': self.timestamp.isoformat(),
            'symbol': self.symbol,
            'alert_type': self.alert_type.value,
            'priority': self.priority.value,
            'title': self.title,
            'description': self.description,
            'data': self.data,
            'action_required': self.action_required
        }

class MarketConditionMonitor:
    """Monitors various market conditions"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.thresholds = config.get('thresholds', {})
        self.active_alerts = {}

    def check_price_breakout(self, symbol: str, df: pd.DataFrame) -> Optional[MarketAlert]:
        """Check for price breakouts"""
        try:
            current_price = df['close'].iloc[-1]

            # Calculate resistance and support
            high_20 = df['high'].rolling(20).max().iloc[-1]
            low_20 = df['low'].rolling(20).min().iloc[-1]

            # Check breakout
            if current_price > high_20 * 1.01:  # 1% above resistance
                return MarketAlert(
                    alert_id=f"PB_{symbol}_{datetime.now().timestamp()}",
                    timestamp=datetime.now(),
                    symbol=symbol,
                    alert_type=AlertType.PRICE_BREAKOUT,
                    priority=AlertPriority.HIGH,
                    title=f"{symbol} Resistance Breakout",
                    description=f"{symbol} broke above 20-day high at {high_20:.2f}",
                    data={
                        'current_price': current_price,
                        'resistance': high_20,
                        'breakout_strength': (current_price - high_20) / high_20
                    },
                    action_required=True
                )
            elif current_price < low_20 * 0.99:  # 1% below support
                return MarketAlert(
                    alert_id=f"PB_{symbol}_{datetime.now().timestamp()}",
                    timestamp=datetime.now(),
                    symbol=symbol,
                    alert_type=AlertType.PRICE_BREAKOUT,
                    priority=AlertPriority.HIGH,
                    title=f"{symbol} Support Breakdown",
                    description=f"{symbol} broke below 20-day low at {low_20:.2f}",
                    data={
                        'current_price': current_price,
                        'support': low_20,
                        'breakdown_strength': (low_20 - current_price) / low_20
                    },
                    action_required=True
                )

            return None

        except Exception as e:
            logger.error(f"Error checking price breakout: {e}")
            return None

    def check_volume_anomaly(self, symbol: str, df: pd.DataFrame) -> Optional[MarketAlert]:
        """Check for volume anomalies"""
        try:
            if 'volume' not in df.columns:
                return None

            current_volume = df['volume'].iloc[-1]
            avg_volume = df['volume'].rolling(20).mean().iloc[-1]
            volume_ratio = current_volume / avg_volume

            threshold = self.thresholds.get('volume_spike', 2.0)

            if volume_ratio > threshold:
                return MarketAlert(
                    alert_id=f"VS_{symbol}_{datetime.now().timestamp()}",
                    timestamp=datetime.now(),
                    symbol=symbol,
                    alert_type=AlertType.VOLUME_SPIKE,
                    priority=AlertPriority.MEDIUM,
                    title=f"{symbol} Volume Spike",
                    description=f"Volume {volume_ratio:.1f}x above average",
                    data={
                        'current_volume': current_volume,
                        'average_volume': avg_volume,
                        'volume_ratio': volume_ratio
                    }
                )

            return None

        except Exception as e:
            logger.error(f"Error checking volume anomaly: {e}")
            return None

    def check_volatility_threshold(self, symbol: str, df: pd.DataFrame) -> Optional[MarketAlert]:
        """Check if volatility exceeds thresholds"""
        try:
            returns = df['close'].pct_change()
            current_volatility = returns.rolling(20).std().iloc[-1] * np.sqrt(252)

            vol_threshold = self.thresholds.get('high_volatility', 0.5)

            if current_volatility > vol_threshold:
                return MarketAlert(
                    alert_id=f"VA_{symbol}_{datetime.now().timestamp()}",
                    timestamp=datetime.now(),
                    symbol=symbol,
                    alert_type=AlertType.VOLATILITY_ALERT,
                    priority=AlertPriority.HIGH,
                    title=f"{symbol} High Volatility",
                    description=f"Annualized volatility at {current_volatility:.1%}",
                    data={
                        'current_volatility': current_volatility,
                        'threshold': vol_threshold
                    },
                    action_required=True
                )

            return None

        except Exception as e:
            logger.error(f"Error checking volatility: {e}")
            return None

class TechnicalIndicatorMonitor:
    """Monitors technical indicators for signals"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.indicators = config.get('indicators', ['rsi', 'macd', 'bb'])

    def check_rsi_signals(self, symbol: str, df: pd.DataFrame) -> Optional[MarketAlert]:
        """Check RSI for overbought/oversold conditions"""
        try:
            # Calculate RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))

            current_rsi = rsi.iloc[-1]

            if current_rsi > 70:
                return MarketAlert(
                    alert_id=f"RSI_{symbol}_{datetime.now().timestamp()}",
                    timestamp=datetime.now(),
                    symbol=symbol,
                    alert_type=AlertType.INDICATOR_SIGNAL,
                    priority=AlertPriority.MEDIUM,
                    title=f"{symbol} RSI Overbought",
                    description=f"RSI at {current_rsi:.1f} - potential reversal",
                    data={'rsi': current_rsi, 'condition': 'overbought'}
                )
            elif current_rsi < 30:
                return MarketAlert(
                    alert_id=f"RSI_{symbol}_{datetime.now().timestamp()}",
                    timestamp=datetime.now(),
                    symbol=symbol,
                    alert_type=AlertType.INDICATOR_SIGNAL,
                    priority=AlertPriority.MEDIUM,
                    title=f"{symbol} RSI Oversold",
                    description=f"RSI at {current_rsi:.1f} - potential bounce",
                    data={'rsi': current_rsi, 'condition': 'oversold'}
                )

            return None

        except Exception as e:
            logger.error(f"Error checking RSI: {e}")
            return None

    def check_macd_crossover(self, symbol: str, df: pd.DataFrame) -> Optional[MarketAlert]:
        """Check for MACD crossovers"""
        try:
            # Calculate MACD
            exp1 = df['close'].ewm(span=12, adjust=False).mean()
            exp2 = df['close'].ewm(span=26, adjust=False).mean()
            macd = exp1 - exp2
            signal = macd.ewm(span=9, adjust=False).mean()

            # Check for crossover
            macd_current = macd.iloc[-1]
            macd_prev = macd.iloc[-2]
            signal_current = signal.iloc[-1]
            signal_prev = signal.iloc[-2]

            if macd_prev <= signal_prev and macd_current > signal_current:
                return MarketAlert(
                    alert_id=f"MACD_{symbol}_{datetime.now().timestamp()}",
                    timestamp=datetime.now(),
                    symbol=symbol,
                    alert_type=AlertType.INDICATOR_SIGNAL,
                    priority=AlertPriority.MEDIUM,
                    title=f"{symbol} MACD Bullish Crossover",
                    description="MACD crossed above signal line",
                    data={
                        'macd': macd_current,
                        'signal': signal_current,
                        'crossover': 'bullish'
                    }
                )
            elif macd_prev >= signal_prev and macd_current < signal_current:
                return MarketAlert(
                    alert_id=f"MACD_{symbol}_{datetime.now().timestamp()}",
                    timestamp=datetime.now(),
                    symbol=symbol,
                    alert_type=AlertType.INDICATOR_SIGNAL,
                    priority=AlertPriority.MEDIUM,
                    title=f"{symbol} MACD Bearish Crossover",
                    description="MACD crossed below signal line",
                    data={
                        'macd': macd_current,
                        'signal': signal_current,
                        'crossover': 'bearish'
                    }
                )

            return None

        except Exception as e:
            logger.error(f"Error checking MACD: {e}")
            return None

class PatternMonitor:
    """Monitors for pattern completions"""

    def check_patterns(self, symbol: str, df: pd.DataFrame, patterns: Dict[str, Any]) -> List[MarketAlert]:
        """Check for pattern completions"""
        alerts = []

        try:
            # Check each detected pattern
            for pattern_type, pattern_data in patterns.items():
                if pattern_data.get('confidence', 0) > 0.7:
                    if pattern_data.get('status') == 'completed':
                        alert = MarketAlert(
                            alert_id=f"PAT_{symbol}_{pattern_type}_{datetime.now().timestamp()}",
                            timestamp=datetime.now(),
                            symbol=symbol,
                            alert_type=AlertType.PATTERN_COMPLETE,
                            priority=AlertPriority.HIGH,
                            title=f"{symbol} {pattern_type} Pattern Complete",
                            description=f"{pattern_type} pattern completed with {pattern_data['confidence']:.0%} confidence",
                            data=pattern_data,
                            action_required=True
                        )
                        alerts.append(alert)

        except Exception as e:
            logger.error(f"Error checking patterns: {e}")

        return alerts

class RiskMonitor:
    """Monitors portfolio risk metrics"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.risk_limits = config.get('risk_limits', {})

    def check_risk_thresholds(self, portfolio_data: Dict[str, Any]) -> List[MarketAlert]:
        """Check if risk metrics exceed thresholds"""
        alerts = []

        try:
            # Check drawdown
            max_dd_limit = self.risk_limits.get('max_drawdown', 0.2)
            current_dd = portfolio_data.get('current_drawdown', 0)

            if abs(current_dd) > max_dd_limit:
                alert = MarketAlert(
                    alert_id=f"RISK_DD_{datetime.now().timestamp()}",
                    timestamp=datetime.now(),
                    symbol="PORTFOLIO",
                    alert_type=AlertType.RISK_THRESHOLD,
                    priority=AlertPriority.CRITICAL,
                    title="Maximum Drawdown Exceeded",
                    description=f"Portfolio drawdown at {abs(current_dd):.1%}",
                    data={
                        'current_drawdown': current_dd,
                        'limit': max_dd_limit
                    },
                    action_required=True
                )
                alerts.append(alert)

            # Check position concentration
            max_position = self.risk_limits.get('max_position_size', 0.3)
            positions = portfolio_data.get('positions', {})

            for symbol, position in positions.items():
                if position.get('allocation', 0) > max_position:
                    alert = MarketAlert(
                        alert_id=f"RISK_POS_{symbol}_{datetime.now().timestamp()}",
                        timestamp=datetime.now(),
                        symbol=symbol,
                        alert_type=AlertType.RISK_THRESHOLD,
                        priority=AlertPriority.HIGH,
                        title=f"Position Size Limit Exceeded - {symbol}",
                        description=f"Position at {position['allocation']:.1%} of portfolio",
                        data={
                            'current_allocation': position['allocation'],
                            'limit': max_position
                        },
                        action_required=True
                    )
                    alerts.append(alert)

        except Exception as e:
            logger.error(f"Error checking risk thresholds: {e}")

        return alerts

class MarketMonitor:
    """Main market monitoring system"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.condition_monitor = MarketConditionMonitor(config)
        self.indicator_monitor = TechnicalIndicatorMonitor(config)
        self.pattern_monitor = PatternMonitor()
        self.risk_monitor = RiskMonitor(config)
        self.alerts = []
        self.alert_callbacks = []

    def add_alert_callback(self, callback: Callable[[MarketAlert], None]):
        """Add callback for alert notifications"""
        self.alert_callbacks.append(callback)

    def process_market_data(self, market_data: Dict[str, pd.DataFrame], 
                          patterns: Dict[str, Dict] = None,
                          portfolio_data: Dict[str, Any] = None) -> List[MarketAlert]:
        """Process market data and generate alerts"""
        new_alerts = []

        # Check each symbol
        for symbol, df in market_data.items():
            # Market conditions
            alert = self.condition_monitor.check_price_breakout(symbol, df)
            if alert:
                new_alerts.append(alert)

            alert = self.condition_monitor.check_volume_anomaly(symbol, df)
            if alert:
                new_alerts.append(alert)

            alert = self.condition_monitor.check_volatility_threshold(symbol, df)
            if alert:
                new_alerts.append(alert)

            # Technical indicators
            alert = self.indicator_monitor.check_rsi_signals(symbol, df)
            if alert:
                new_alerts.append(alert)

            alert = self.indicator_monitor.check_macd_crossover(symbol, df)
            if alert:
                new_alerts.append(alert)

            # Patterns
            if patterns and symbol in patterns:
                pattern_alerts = self.pattern_monitor.check_patterns(
                    symbol, df, patterns[symbol]
                )
                new_alerts.extend(pattern_alerts)

        # Risk monitoring
        if portfolio_data:
            risk_alerts = self.risk_monitor.check_risk_thresholds(portfolio_data)
            new_alerts.extend(risk_alerts)

        # Process new alerts
        for alert in new_alerts:
            self._process_alert(alert)

        return new_alerts

    def _process_alert(self, alert: MarketAlert):
        """Process individual alert"""
        # Add to alerts list
        self.alerts.append(alert)

        # Trigger callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")

        # Log alert
        logger.info(f"Alert: {alert.title} - {alert.description}")

    def get_active_alerts(self, priority: AlertPriority = None) -> List[MarketAlert]:
        """Get active alerts, optionally filtered by priority"""
        if priority:
            return [a for a in self.alerts if a.priority == priority]
        return self.alerts

    def clear_old_alerts(self, hours: int = 24):
        """Clear alerts older than specified hours"""
        cutoff = datetime.now() - timedelta(hours=hours)
        self.alerts = [a for a in self.alerts if a.timestamp > cutoff]

    def export_alerts(self, filepath: str):
        """Export alerts to JSON file"""
        alerts_data = [alert.to_dict() for alert in self.alerts]
        with open(filepath, 'w') as f:
            json.dump(alerts_data, f, indent=2)

# Example configuration
DEFAULT_CONFIG = {
    "thresholds": {
        "volume_spike": 2.0,
        "high_volatility": 0.5,
        "price_change": 0.05
    },
    "indicators": ["rsi", "macd", "bb"],
    "risk_limits": {
        "max_drawdown": 0.2,
        "max_position_size": 0.3,
        "max_correlation": 0.8
    },
    "alert_settings": {
        "min_priority": 2,
        "max_alerts_per_symbol": 5
    }
}

# Example usage
if __name__ == "__main__":
    # Create monitor
    monitor = MarketMonitor(DEFAULT_CONFIG)

    # Add alert callback
    def alert_handler(alert: MarketAlert):
        print(f"\n🚨 ALERT: {alert.title}")
        print(f"   Priority: {alert.priority.name}")
        print(f"   {alert.description}")
        if alert.action_required:
            print("   ⚠️  ACTION REQUIRED")

    monitor.add_alert_callback(alert_handler)

    # Create sample data
    dates = pd.date_range(start='2024-01-01', end='2024-06-01', freq='H')

    # Simulate market data with some anomalies
    market_data = {
        'BTC-USD': pd.DataFrame({
            'close': np.random.randn(len(dates)).cumsum() + 50000,
            'high': np.random.randn(len(dates)).cumsum() + 50100,
            'low': np.random.randn(len(dates)).cumsum() + 49900,
            'volume': np.where(
                np.random.random(len(dates)) > 0.95,
                np.random.randint(5000000, 10000000, len(dates)),  # Volume spikes
                np.random.randint(1000000, 2000000, len(dates))
            )
        }, index=dates)
    }

    # Process data
    alerts = monitor.process_market_data(market_data)

    print(f"\nGenerated {len(alerts)} alerts")

    # Export alerts
    monitor.export_alerts('market_alerts.json')
