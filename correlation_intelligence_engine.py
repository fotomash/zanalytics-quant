import json
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List

import numpy as np
import pandas as pd
import redis


@dataclass
class CorrelationAlert:
    """Container for correlation alert information."""

    asset_pair: str
    correlation: float
    threshold_breach: bool
    severity: str
    timestamp: datetime
    regime_change: bool


class LLMNativeCorrelationEngine:
    """Correlation analysis engine designed for LLM integrations."""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.correlation_thresholds = {
            "DXY_VIX": 0.75,
            "BTC_SPX": 0.95,
            "ETH_BTC": 0.95,
            "GOLD_DXY": -0.85,
        }

        # Baseline correlations used as reference values
        self.baseline_correlations = {
            "SPX_BTC": 0.98,
            "SPX_ETH": 0.98,
            "BTC_ETH": 0.99,
            "DXY_VIX": 0.83,
            "GOLD_VIX": -0.90,
            "SPX_VIX": -0.94,
        }

    def analyze_correlation_regime(self, current_data: Dict[str, List[float]]) -> List[CorrelationAlert]:
        """Compare current correlations against baselines and detect anomalies."""
        alerts: List[CorrelationAlert] = []

        for pair, baseline in self.baseline_correlations.items():
            current_corr = self._calculate_rolling_correlation(pair, current_data)
            if current_corr is None:
                continue

            threshold = self.correlation_thresholds.get(pair, 0.8)
            breach = abs(current_corr - baseline) > (1 - threshold)
            severity = self._determine_severity(pair, current_corr, baseline)

            alert = CorrelationAlert(
                asset_pair=pair,
                correlation=current_corr,
                threshold_breach=breach,
                severity=severity,
                timestamp=datetime.now(),
                regime_change=breach and severity == "critical",
            )
            alerts.append(alert)
            self._store_correlation_alert(alert)

        return alerts

    def _calculate_rolling_correlation(
        self, pair: str, data: Dict[str, List[float]], window: int = 20
    ) -> float | None:
        """Calculate rolling correlation for an asset pair."""
        assets = pair.split("_")
        if len(assets) != 2:
            return None

        asset1_data = data.get(assets[0])
        asset2_data = data.get(assets[1])
        if not asset1_data or not asset2_data:
            return None

        s1 = pd.Series(asset1_data[-window:])
        s2 = pd.Series(asset2_data[-window:])
        return s1.corr(s2)

    def _determine_severity(self, pair: str, current: float, baseline: float) -> str:
        """Derive severity level based on deviation from baseline."""
        deviation = abs(current - baseline)
        if pair == "DXY_VIX" and current > 0.8:
            return "critical"
        if deviation > 0.3:
            return "critical"
        if deviation > 0.2:
            return "high"
        if deviation > 0.1:
            return "medium"
        return "low"

    def _store_correlation_alert(self, alert: CorrelationAlert) -> None:
        """Persist alert details in Redis for later consumption."""
        alert_data = {
            "asset_pair": alert.asset_pair,
            "correlation": alert.correlation,
            "threshold_breach": alert.threshold_breach,
            "severity": alert.severity,
            "timestamp": alert.timestamp.isoformat(),
            "regime_change": alert.regime_change,
        }
        key = f"correlation_alert:{alert.asset_pair}:{int(alert.timestamp.timestamp())}"
        self.redis.setex(key, 3600, json.dumps(alert_data))
        latest_key = f"latest_correlation:{alert.asset_pair}"
        self.redis.set(latest_key, json.dumps(alert_data))

    def get_llm_correlation_summary(self) -> Dict[str, object]:
        """Provide an LLM-friendly summary of correlation conditions."""
        summary: Dict[str, object] = {
            "timestamp": datetime.now().isoformat(),
            "critical_alerts": [],
            "regime_changes": [],
            "correlation_matrix": {},
            "anomalies": [],
        }

        for pair in self.baseline_correlations:
            key = f"latest_correlation:{pair}"
            data = self.redis.get(key)
            if not data:
                continue
            alert_data = json.loads(data)
            summary["correlation_matrix"][pair] = alert_data["correlation"]
            if alert_data.get("severity") == "critical":
                summary["critical_alerts"].append(alert_data)
            if alert_data.get("regime_change"):
                summary["regime_changes"].append(alert_data)
            if pair == "DXY_VIX" and alert_data["correlation"] > 0.75:
                summary["anomalies"].append(
                    {
                        "type": "dxy_vix_crisis_correlation",
                        "value": alert_data["correlation"],
                        "expected": "negative_correlation",
                        "implication": "potential_market_stress",
                    }
                )

        return summary
