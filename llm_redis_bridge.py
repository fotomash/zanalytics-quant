import json
from datetime import datetime
from typing import Any, Dict, List

import redis


class LLMRedisBridge:
    """Structured access layer between Redis and LLM agents."""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.llm_namespace = "llm_agent"

    def store_llm_context(self, agent_id: str, context: Dict[str, Any]) -> None:
        """Persist context for an LLM agent in Redis."""
        key = f"{self.llm_namespace}:context:{agent_id}"
        structured_context = {
            "timestamp": datetime.now().isoformat(),
            "agent_id": agent_id,
            "market_data": context.get("market_data", {}),
            "correlations": context.get("correlations", {}),
            "alerts": context.get("alerts", []),
            "analysis_results": context.get("analysis_results", {}),
            "trading_signals": context.get("trading_signals", []),
        }
        self.redis.setex(key, 1800, json.dumps(structured_context))

    def get_market_intelligence_summary(self) -> Dict[str, Any]:
        """Build a market intelligence summary for LLM consumption."""
        return {
            "timestamp": datetime.now().isoformat(),
            "market_overview": self._get_market_overview(),
            "correlation_analysis": self._get_correlation_analysis(),
            "technical_signals": self._get_technical_signals(),
            "risk_alerts": self._get_risk_alerts(),
            "wyckoff_analysis": self._get_wyckoff_analysis(),
            "smc_analysis": self._get_smc_analysis(),
        }

    def _get_market_overview(self) -> Dict[str, Any]:
        overview: Dict[str, Any] = {}
        for asset in ["BTC", "ETH", "SPX", "DXY", "GOLD", "VIX"]:
            price_key = f"price:{asset}"
            price_data = self.redis.get(price_key)
            if price_data:
                overview[asset] = json.loads(price_data)
        return overview

    def _get_correlation_analysis(self) -> Dict[str, Any]:
        correlations: Dict[str, Any] = {}
        for key in self.redis.keys("latest_correlation:*"):
            pair = key.decode().split(":")[1]
            data = self.redis.get(key)
            if data:
                correlations[pair] = json.loads(data)
        return correlations

    def _get_technical_signals(self) -> List[Dict[str, Any]]:
        signals: List[Dict[str, Any]] = []
        for key in self.redis.keys("technical_signal:*"):
            data = self.redis.get(key)
            if data:
                signals.append(json.loads(data))
        return signals

    def _get_risk_alerts(self) -> List[Dict[str, Any]]:
        alerts: List[Dict[str, Any]] = []
        for key in self.redis.keys("correlation_alert:*"):
            data = self.redis.get(key)
            if data:
                alert_data = json.loads(data)
                if alert_data.get("severity") in ["critical", "high"]:
                    alerts.append(alert_data)
        return alerts

    def _get_wyckoff_analysis(self) -> Dict[str, Any]:
        key = "wyckoff_analysis:latest"
        data = self.redis.get(key)
        return json.loads(data) if data else {}

    def _get_smc_analysis(self) -> Dict[str, Any]:
        key = "smc_analysis:latest"
        data = self.redis.get(key)
        return json.loads(data) if data else {}

    def create_llm_tool_response(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Return structured responses for tool calls used by LLM agents."""
        if tool_name == "get_market_intelligence":
            return self.get_market_intelligence_summary()
        if tool_name == "get_correlation_alert":
            asset_pair = parameters.get("asset_pair", "DXY_VIX")
            key = f"latest_correlation:{asset_pair}"
            data = self.redis.get(key)
            if data:
                return {
                    "status": "success",
                    "data": json.loads(data),
                    "timestamp": datetime.now().isoformat(),
                }
            return {
                "status": "no_data",
                "message": f"No correlation data available for {asset_pair}",
                "timestamp": datetime.now().isoformat(),
            }
        if tool_name == "get_trading_signals":
            return {
                "status": "success",
                "signals": self._get_technical_signals(),
                "timestamp": datetime.now().isoformat(),
            }
        return {
            "status": "error",
            "message": f"Unknown tool: {tool_name}",
            "timestamp": datetime.now().isoformat(),
        }
