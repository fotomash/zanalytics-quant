"""Simplified PulseKernel implementation used by the demo dashboard."""
import json
import os
import yaml
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import random

class PulseKernel:
    """Lightweight orchestration engine for demo purposes."""

    def __init__(self, config_path: str | None = None):
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "pulse_dashboard_config.yaml",
            )
        self.config = self._load_config(config_path)
        self.confluence_scorer = ConfluenceScorer(self.config)
        self.risk_enforcer = RiskEnforcer(self.config)
        self.signal_journal = SignalJournal()
        self.active_signals: Dict[str, Dict] = {}
        self.system_state = "INITIALIZED"

    def _load_config(self, path: str) -> Dict:
        try:
            with open(path, "r") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            return {
                "confluence_weights": {"smc": 0.4, "wyckoff": 0.3, "technical": 0.3},
                "risk_limits": {
                    "daily_loss_limit": 0.03,
                    "max_trades_per_day": 5,
                    "cooling_off_minutes": 15,
                    "min_confluence_score": 70,
                },
            }

    def process_tick(self, market_data: Dict) -> Optional[Dict]:
        score = self.confluence_scorer.calculate(market_data)
        risk = self.risk_enforcer.check_constraints(score)
        self.signal_journal.log_analysis({
            "timestamp": datetime.now().isoformat(),
            "confluence_score": score,
            "risk_status": risk,
        })
        if risk["allowed"]:
            signal = self._generate_signal(market_data, score, risk)
            self.active_signals[signal["id"]] = signal
            self.signal_journal.log_signal(signal)
            return signal
        return None

    def _generate_signal(self, market_data: Dict, score: float, risk: Dict) -> Dict:
        return {
            "id": f"SIG_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "timestamp": datetime.now().isoformat(),
            "symbol": market_data.get("symbol", "UNKNOWN"),
            "action": self._determine_action(score),
            "confluence_score": score,
            "risk_assessment": risk,
            "entry_price": market_data.get("price", 0.0),
            "stop_loss": self._calculate_stop_loss(market_data),
            "take_profit": self._calculate_take_profit(market_data),
            "position_size": self._calculate_position_size(risk),
        }

    def _determine_action(self, score: float) -> str:
        if score >= 80:
            return "STRONG_BUY" if random.random() > 0.5 else "STRONG_SELL"
        if score >= 70:
            return "BUY" if random.random() > 0.5 else "SELL"
        return "HOLD"

    def _calculate_stop_loss(self, market_data: Dict) -> float:
        price = market_data.get("price", 100)
        return price * 0.98

    def _calculate_take_profit(self, market_data: Dict) -> float:
        price = market_data.get("price", 100)
        return price * 1.05

    def _calculate_position_size(self, risk: Dict) -> float:
        base = 1.0
        if risk.get("risk_level") == "HIGH":
            return base * 0.5
        if risk.get("risk_level") == "MEDIUM":
            return base * 0.75
        return base

    def get_system_status(self) -> Dict:
        return {
            "state": self.system_state,
            "active_signals": len(self.active_signals),
            "risk_status": self.risk_enforcer.get_status(),
            "last_update": datetime.now().isoformat(),
        }

class ConfluenceScorer:
    def __init__(self, config: Dict):
        w = config.get("confluence_weights", {})
        self.smc_weight = w.get("smc", 0.4)
        self.wyckoff_weight = w.get("wyckoff", 0.3)
        self.technical_weight = w.get("technical", 0.3)

    def calculate(self, market_data: Dict) -> float:
        smc = random.uniform(60, 95)
        wyckoff = random.uniform(60, 95)
        technical = random.uniform(60, 95)
        total = (
            smc * self.smc_weight
            + wyckoff * self.wyckoff_weight
            + technical * self.technical_weight
        )
        return min(100, max(0, total))

class RiskEnforcer:
    def __init__(self, config: Dict):
        c = config.get("risk_limits", {})
        self.daily_loss_limit = c.get("daily_loss_limit", 0.03)
        self.max_trades_per_day = c.get("max_trades_per_day", 5)
        self.cooling_off_minutes = c.get("cooling_off_minutes", 15)
        self.min_confluence_score = c.get("min_confluence_score", 70)
        self.trades_today = 0
        self.daily_pnl = 0.0
        self.last_trade_time = None
        self.consecutive_wins = 0
        self.consecutive_losses = 0
        self.is_cooling_off = False

    def check_constraints(self, score: float) -> Dict:
        result = {"allowed": True, "risk_level": "LOW", "warnings": [], "blocks": []}
        if score < self.min_confluence_score:
            result["allowed"] = False
            result["blocks"].append("Confluence below threshold")
        if self.trades_today >= self.max_trades_per_day:
            result["allowed"] = False
            result["blocks"].append("Trade limit reached")
        if abs(self.daily_pnl) > (self.daily_loss_limit * 10000):
            result["allowed"] = False
            result["blocks"].append("Daily loss limit exceeded")
        if self.is_cooling_off:
            if self.last_trade_time and (
                datetime.now() - self.last_trade_time
            ).total_seconds() < self.cooling_off_minutes * 60:
                result["allowed"] = False
                result["blocks"].append("Cooling off")
            else:
                self.is_cooling_off = False
        if len(result["blocks"]) > 0:
            result["risk_level"] = "HIGH"
        return result

    def update_trade_result(self, pnl: float):
        self.trades_today += 1
        self.daily_pnl += pnl
        self.last_trade_time = datetime.now()
        if pnl > 0:
            self.consecutive_wins += 1
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1
            self.consecutive_wins = 0
        if self.consecutive_losses >= 2 or abs(pnl) > 500:
            self.is_cooling_off = True

    def get_status(self) -> Dict:
        return {
            "trades_today": self.trades_today,
            "daily_pnl": self.daily_pnl,
            "consecutive_wins": self.consecutive_wins,
            "consecutive_losses": self.consecutive_losses,
            "is_cooling_off": self.is_cooling_off,
        }

class SignalJournal:
    def __init__(self, log_file: str = "signal_journal.json"):
        self.log_file = log_file
        self.entries: List[Dict] = []
        self._load_existing()

    def _load_existing(self):
        try:
            with open(self.log_file, "r") as f:
                self.entries = json.load(f)
        except FileNotFoundError:
            self.entries = []

    def _save(self):
        with open(self.log_file, "w") as f:
            json.dump(self.entries[-1000:], f, indent=2)

    def log_analysis(self, data: Dict):
        self.entries.append({"timestamp": datetime.now().isoformat(), "type": "analysis", "data": data})
        self._save()

    def log_signal(self, signal: Dict):
        self.entries.append({"timestamp": datetime.now().isoformat(), "type": "signal", "data": signal})
        self._save()

    def log_trade_result(self, trade_id: str, result: Dict):
        self.entries.append(
            {
                "timestamp": datetime.now().isoformat(),
                "type": "trade_result",
                "trade_id": trade_id,
                "data": result,
            }
        )
        self._save()

    def get_recent_entries(self, count: int = 10) -> List[Dict]:
        return self.entries[-count:]

if __name__ == "__main__":
    pulse = PulseKernel()
    md = {"symbol": "EURUSD", "price": 1.0850, "volume": 1_000_000, "timestamp": datetime.now().isoformat()}
    sig = pulse.process_tick(md)
    if sig:
        print(json.dumps(sig, indent=2))
    print(json.dumps(pulse.get_system_status(), indent=2))
