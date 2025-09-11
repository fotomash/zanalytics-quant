"""Simple risk enforcement utility.

Provides basic pre-trade checks to prevent common rule breaches such as
exceeding daily loss limits or trading too frequently.  State is kept in
memory; production deployments should persist the trade history in a
database or cache.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Dict, List

import yaml


@dataclass
class RiskEnforcer:
    """Guardian object that evaluates trades against risk limits."""

    config_path: str = "pulse_config.yaml"
    daily_max_loss: float = field(init=False, default=500.0)
    risk_per_trade: float = field(init=False, default=0.01)
    max_trades_per_day: int = field(init=False, default=5)
    cooldown_after_loss: _dt.timedelta = field(init=False, default=_dt.timedelta(minutes=15))
    trade_history: List[Dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        try:
            with open(self.config_path, "r") as f:
                cfg = yaml.safe_load(f) or {}
        except FileNotFoundError as exc:  # pragma: no cover - explicit for clarity
            raise ValueError("Config file not found - using defaults may compromise safety.") from exc

        self.daily_max_loss = cfg.get("DAILY_MAX_LOSS", self.daily_max_loss)
        self.risk_per_trade = cfg.get("RISK_PER_TRADE", self.risk_per_trade)
        self.max_trades_per_day = cfg.get("MAX_TRADES_PER_DAY", self.max_trades_per_day)
        self.cooldown_after_loss = _dt.timedelta(
            minutes=cfg.get("COOLDOWN_AFTER_LOSS", int(self.cooldown_after_loss.total_seconds() // 60))
        )

    # ------------------------------------------------------------------
    def check_trade(self, proposed_trade: Dict) -> Dict[str, List[str] | str]:
        """Evaluate a proposed trade.

        Parameters
        ----------
        proposed_trade:
            Dictionary containing ``risk`` and ``account_balance`` fields.

        Returns
        -------
        dict
            ``{"decision": str, "reasons": List[str]}`` where decision is one
            of ``allowed``, ``warning`` or ``blocked``.
        """

        reasons: List[str] = []
        today = _dt.date.today()

        pnl_today = sum(t["pnl"] for t in self.trade_history if t["date"] == today)
        projected_pnl = pnl_today - proposed_trade.get("risk", 0)
        if projected_pnl < -self.daily_max_loss:
            reasons.append("Daily limit exceeded")

        if proposed_trade.get("risk", 0) > self.risk_per_trade * proposed_trade.get("account_balance", 10_000):
            reasons.append("Risk per trade exceeded")

        trades_today = len([t for t in self.trade_history if t["date"] == today])
        if trades_today >= self.max_trades_per_day:
            reasons.append("Max trades per day exceeded")

        last_loss = next((t for t in reversed(self.trade_history) if t["pnl"] < 0), None)
        if last_loss and (_dt.datetime.now() - last_loss["time"]) < self.cooldown_after_loss:
            reasons.append("Cooldown after loss - potential revenge trading")

        if trades_today > 3 and all(t["pnl"] > 0 for t in self.trade_history[-3:]):
            reasons.append("Overconfidence alert - consider pausing")

        decision = (
            "blocked" if any("exceeded" in r for r in reasons) else "warning" if reasons else "allowed"
        )
        return {"decision": decision, "reasons": reasons}

    # ------------------------------------------------------------------
    def record_trade(self, trade: Dict) -> None:
        """Add a completed trade to history."""

        trade["date"] = _dt.date.today()
        trade["time"] = _dt.datetime.now()
        self.trade_history.append(trade)
