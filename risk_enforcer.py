"""Behavioral risk management layer.

The :class:`RiskEnforcer` implements a number of lightweight
behavioural protection mechanisms inspired by research on trader
psychology.  It tracks session statistics and determines whether a
new trade is permitted.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, date
from typing import Dict, Any, Tuple


@dataclass
class RiskEnforcer:
    """Manage behavioural risk limits.

    Parameters
    ----------
    balance:
        Account balance used for percentage based calculations.
    max_daily_loss_pct:
        Soft daily loss threshold (e.g. 3%).
    hard_loss_pct:
        Hard daily loss limit (e.g. 5%).
    max_trades:
        Maximum number of trades per session.
    cool_off_minutes:
        Mandatory break after each trade.
    disposition_pct:
        Maximum allowed unrealised loss per trade.
    max_loss_streak:
        Consecutive losing trades allowed before enforcing a break.
    """

    balance: float = 1_0000.0
    max_daily_loss_pct: float = 0.03
    hard_loss_pct: float = 0.05
    max_trades: int = 10
    cool_off_minutes: int = 15
    disposition_pct: float = 0.01
    max_loss_streak: int = 3

    # Internal state
    _trade_count: int = 0
    _daily_loss: float = 0.0
    _last_trade: datetime | None = None
    _loss_streak: int = 0
    _rules_locked: bool = False
    _day: date = field(default_factory=lambda: datetime.utcnow().date())

    # ------------------------------------------------------------------
    # Life-cycle helpers
    # ------------------------------------------------------------------
    def lock_rules(self) -> None:
        """Prevent further modification of parameters."""
        self._rules_locked = True

    def _check_new_day(self, now: datetime) -> None:
        if now.date() != self._day:
            self._day = now.date()
            self._trade_count = 0
            self._daily_loss = 0.0
            self._loss_streak = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def evaluate(
        self,
        trade: Dict[str, Any] | None = None,
        now: datetime | None = None,
        features: Dict[str, Any] | None = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """Evaluate whether trading is allowed.

        Parameters
        ----------
        trade:
            Optional trade information containing ``pnl``.
        now:
            Timestamp for evaluation; defaults to current UTC time.
        """
        now = now or datetime.utcnow()
        self._check_new_day(now)

        reasons = []
        allowed = True

        if not self._rules_locked:
            allowed = False
            reasons.append("rules_not_locked")

        if self._last_trade and now - self._last_trade < timedelta(minutes=self.cool_off_minutes):
            allowed = False
            reasons.append("cooling_off")

        if self._trade_count >= self.max_trades:
            allowed = False
            reasons.append("max_trades_reached")

        if (self._daily_loss / self.balance) >= self.hard_loss_pct:
            allowed = False
            reasons.append("hard_daily_loss")
        elif (self._daily_loss / self.balance) >= self.max_daily_loss_pct:
            allowed = False
            reasons.append("daily_loss_limit")

        if self._loss_streak >= self.max_loss_streak:
            allowed = False
            reasons.append("loss_streak")

        if features and features.get("news_active"):
            allowed = False
            reasons.append("news_window")

        if trade is not None:
            pnl = float(trade.get("pnl", 0))
            self._register_trade(pnl, now)

        state = {
            "trade_count": self._trade_count,
            "daily_loss": self._daily_loss,
            "loss_streak": self._loss_streak,
        }
        return allowed, {"reasons": reasons, "state": state}

    # ------------------------------------------------------------------
    # Compatibility helper
    # ------------------------------------------------------------------
    def check(self, ts, symbol, score: float, features: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """Simplified check interface used by the streaming kernel.

        Parameters
        ----------
        ts, symbol:
            Currently unused but kept for API compatibility.
        score:
            Latest confluence score. Extremely high scores trigger an
            "overconfidence" warning.
        features:
            Optional feature dictionary which may contain ``news_active``.
        """

        reasons = []
        status = "allowed"

        if features and features.get("news_active"):
            return {"status": "blocked", "reason": ["High-impact news window"]}

        if float(score) >= 90:
            reasons.append("Overconfidence clamp: attenuate size")
            status = "warned"

        return {"status": status, "reason": reasons}

    def disposition_exit(self, unrealised_pnl: float) -> bool:
        """Return ``True`` if a position should be closed."""
        threshold = -self.balance * self.disposition_pct
        return unrealised_pnl <= threshold

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _register_trade(self, pnl: float, now: datetime) -> None:
        self._trade_count += 1
        self._last_trade = now
        if pnl < 0:
            self._daily_loss += abs(pnl)
            self._loss_streak += 1
        else:
            self._loss_streak = 0

