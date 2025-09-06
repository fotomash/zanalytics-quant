from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List
import logging


@dataclass
class Alert:
    type: str
    severity: str
    title: str
    message: str
    data: Dict
    timestamp: datetime
    channels: List[str]


class AlertManager:
    """Simplified alert manager placeholder."""

    def __init__(self):
        self.alert_history: List[Alert] = []
        logging.info("AlertManager initialized")

    def send_alert(self, alert: Alert) -> Dict:
        """Record alert and return result for each channel."""
        self.alert_history.append(alert)
        return {ch: {'success': False, 'error': 'channel not configured'} for ch in alert.channels}

    def create_price_alert(self, symbol: str, current_price: float, threshold: float,
                           direction: str, channels: List[str] | None = None) -> Alert:
        if channels is None:
            channels = ['telegram']
        severity = 'high' if abs(current_price - threshold) / threshold > 0.05 else 'medium'
        return Alert(
            type='price',
            severity=severity,
            title=f"Price Alert: {symbol}",
            message=f"{symbol} has moved {direction} to ${current_price:,.2f} (threshold: ${threshold:,.2f})",
            data={'symbol': symbol, 'current_price': current_price, 'threshold': threshold, 'direction': direction},
            timestamp=datetime.now(),
            channels=channels,
        )
