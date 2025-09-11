"""Utilities for integrating external model outputs with :class:`PulseKernel`.

This module provides simple adapters that can ingest predictions from either
remote ML services or local files.  The resulting signal can then be fed
through the existing :class:`PulseKernel` risk machinery with optional
journaling hooks.

The goal of this lightweight integration layer is to make it easy to
experiment with new modelling approaches while still benefiting from the
risk‑management safeguards already implemented in the core kernel.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable, Dict, Optional

import requests

from pulse_kernel import PulseKernel
from risk_enforcer import EnhancedRiskEnforcer


class MLSignalAdapter:
    """Load model outputs from different sources."""

    @staticmethod
    def from_file(path: str) -> Dict:
        """Load a JSON model output from ``path``.

        The file is expected to contain a mapping with at least a ``score``
        field, but additional information is preserved.
        """

        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)

    @staticmethod
    def from_service(url: str, timeout: int = 5) -> Dict:
        """Fetch model output from an HTTP service returning JSON."""

        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.json()


@dataclass
class PulseKernelV2:
    """Adapter that feeds external signals into :class:`PulseKernel`.

    Parameters
    ----------
    kernel:
        Instance of :class:`PulseKernel` used for state handling.
    risk:
        Optional :class:`EnhancedRiskEnforcer` instance.  If omitted the
        kernel's internal enforcer is used.
    journal_hook:
        Callable receiving the decision dictionary for journaling purposes.
    """

    kernel: PulseKernel
    risk: Optional[EnhancedRiskEnforcer] = None
    journal_hook: Optional[Callable[[Dict], None]] = None

    def __post_init__(self) -> None:  # pragma: no cover - trivial
        if self.risk is None:
            candidate = getattr(self.kernel, "risk_enforcer", None)
            # The repository contains two RiskEnforcer implementations; we
            # only use the one providing ``evaluate_signal``.  If the kernel's
            # enforcer lacks that method we fall back to the richer version
            # imported above.
            if candidate is not None and hasattr(candidate, "evaluate_signal"):
                self.risk = candidate  # kernel already provides enhanced enforcer
            else:
                self.risk = EnhancedRiskEnforcer()
                # Expose core attributes for convenience
                self.risk.limits = self.risk.core.limits
                self.risk.daily_stats = self.risk.core.daily_stats
                self.risk.behavioral_flags = self.risk.core.behavioral_flags
                self.risk.state = self.risk.core.state
                # Ensure essential defaults present
                self.risk.limits.setdefault("max_trades_per_day", 5)
                self.risk.limits.setdefault("daily_loss_limit", 500)

    def process_model_output(self, model_output: Dict) -> Dict:
        """Evaluate a model output through risk checks and journaling.

        The incoming ``model_output`` should at minimum contain a ``score``
        value.  The method returns a decision dictionary containing the risk
        evaluation and an action derived from the score.
        """

        score = float(model_output.get("score", 0))

        # Build signal expected by RiskEnforcer
        signal = {
            "confluence_score": score,
            "session_stats": model_output.get("session_stats", {}),
            "market_data": model_output.get("market_data", {}),
        }

        risk_decision = self.risk.evaluate_signal(signal)

        # Simple policy: trade only on sufficiently strong scores
        action = "trade" if score >= 50 and risk_decision.get("approved") else "hold"

        decision = {
            "score": score,
            "approved": bool(risk_decision.get("approved")),
            "action": action,
            "risk": risk_decision,
        }

        if self.journal_hook:
            try:  # pragma: no cover - journaling errors shouldn't fail pipeline
                self.journal_hook(decision)
            except Exception:
                pass

        # Maintain minimal state for inspection/testing
        self.kernel.active_signals["last"] = decision
        return decision
