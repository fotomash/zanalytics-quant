from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List
from typing import Any, Callable, Dict, List
import logging


@dataclass
class Alert:
    """Data model representing a structured alert."""

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
    """Service for routing alerts to configured channels."""

    def __init__(self, channel_handlers: Dict[str, Callable[[Alert], None]] | None = None):
        self.alert_history: List[Alert] = []
        self.channel_handlers = channel_handlers or {}
        logging.info("AlertManager initialized")

    def register_channel(self, name: str, handler: Callable[[Alert], None]) -> None:
        """Register a handler callable for ``name`` channel."""
        self.channel_handlers[name] = handler

    def send_alert(self, alert: Alert) -> Dict[str, Dict[str, Any]]:
        """Dispatch ``alert`` to requested channels.

        Returns a mapping of channel name to delivery result.
        """
        self.alert_history.append(alert)
        results: Dict[str, Dict[str, Any]] = {}
        for ch in alert.channels:
            handler = self.channel_handlers.get(ch)
            if handler is None:
                results[ch] = {"success": False, "error": "channel not configured"}
                continue
            try:
                handler(alert)
                results[ch] = {"success": True}
            except Exception as exc:  # pragma: no cover - defensive
                results[ch] = {"success": False, "error": str(exc)}
        return results

    def create_price_alert(self, symbol: str, current_price: float, threshold: float,
                           direction: str, channels: List[str] | None = None) -> Alert:
        """Helper to build a standard price alert."""
        if channels is None:
            channels = ["telegram"]
        severity = "high" if abs(current_price - threshold) / threshold > 0.05 else "medium"
        return Alert(
            type="price",
            severity=severity,
            title=f"Price Alert: {symbol}",
            message=f"{symbol} has moved {direction} to ${current_price:,.2f} (threshold: ${threshold:,.2f})",
            data={"symbol": symbol, "current_price": current_price, "threshold": threshold, "direction": direction},
            timestamp=datetime.now(),
            channels=channels,
        )
