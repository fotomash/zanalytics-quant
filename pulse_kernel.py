"""Core streaming kernel for the Pulse package."""

from __future__ import annotations

import json
import yaml
from typing import Optional, Dict, Any

import pandas as pd

from components.smc_analyzer import SMCAnalyzer
from components.wyckoff_scorer import WyckoffScorer
from components.technical_analysis import TechnicalAnalysis
from components.enhanced_analyzer import EnhancedAnalyzer
from components.wyckoff_agents import MultiTFResolver
from confluence_scorer import ConfluenceScorer
from risk_enforcer import RiskEnforcer
from journal_engine import JournalEngine
from alerts.telegram_alerts import notify


class PulseKernel:
    """Process streaming market frames and return scored decisions."""

    def __init__(self, config_path: str = "pulse_config.yaml") -> None:
        try:
            with open(config_path, "r") as f:
                self.config = yaml.safe_load(f)
        except Exception:
            with open(config_path, "r") as f:
                self.config = json.load(f)

        self.smc = SMCAnalyzer()
        self.wyckoff = WyckoffScorer()
        self.tech = TechnicalAnalysis()
        self.enhanced = EnhancedAnalyzer()
        self.scorer = ConfluenceScorer(
            self.smc,
            self.wyckoff,
            self.tech,
            self.enhanced,
            self.config.get("confluence_weights", {}),
        )
        self.risk = RiskEnforcer()
        self.journal = JournalEngine(self.config.get("journal_dir"))
        self.mtf = self.config.get("mtf", {})
        self.mtf_resolver = MultiTFResolver()
        self.mtf_clamp_pts = int(self.mtf.get("clamp_points", 10))
        nb = (self.config.get("wyckoff", {}) or {}).get("news_buffer", {}) or {}
        self.news_cfg = {k: v for k, v in nb.items() if k != "enabled"}
        self.news_enabled = bool(nb.get("enabled"))

    # ------------------------------------------------------------------
    def on_frame(self, frame: Dict[str, Any]) -> Dict[str, Any]:
        """Score a single streaming frame.

        Parameters
        ----------
        frame:
            Dictionary containing at minimum ``ts`` and ``symbol``.  Optionally
            contains bar data for multiple timeframes and feature dictionaries.
        """

        ts, symbol = frame["ts"], frame["symbol"]
        bars = frame.get("bars")
        df = pd.DataFrame(bars) if bars is not None else None

        target: Any
        if df is not None:
            target = df
            news_times = frame.get("news_times") if self.news_enabled else None
            wy_out = self.wyckoff.score(df, news_times=news_times, news_cfg=self.news_cfg)
        else:
            target = frame.get("features", {})
            wy_out = None

        score = self.scorer.score(target)

        if df is not None and frame.get("bars_m5") and frame.get("bars_m15"):
            df5 = pd.DataFrame(frame["bars_m5"])
            df15 = pd.DataFrame(frame["bars_m15"])
            l1 = (wy_out or self.wyckoff.score(df)).get("last_label")
            l5 = self.wyckoff.score(df5).get("last_label")
            l15 = self.wyckoff.score(df15).get("last_label")
            conflict = self.mtf_resolver.resolve(
                pd.Series([l1]), pd.Series([l5]), pd.Series([l15])
            )["conflict_mask"].iloc[-1]
            if bool(conflict):
                score["score"] = max(0.0, float(score["score"]) - self.mtf_clamp_pts)
                score.setdefault("reasons", []).append(
                    f"MTF conflict clamp (-{self.mtf_clamp_pts})"
                )
                score["grade"] = (
                    "Low" if score["score"] < 40 else "Medium" if score["score"] < 70 else "High"
                )

        features = frame.get("features", {})
        decision = self.risk.check(ts, symbol, score["score"], features=features)
        self.journal.log(ts, symbol, score, decision)
        event = {
            "ts": ts,
            "symbol": symbol,
            "score": score.get("score"),
            "grade": score.get("grade"),
            "reasons": score.get("reasons", []),
            "risk_status": decision.get("status"),
            "warnings": decision.get("reason", []) if decision.get("status") == "warned" else [],
            "violations": decision.get("reason", []) if decision.get("status") == "blocked" else [],
            "metrics": features,
            "account": (decision.get("raw") or {}),
        }
        notify(event)
        return {"ts": ts, "symbol": symbol, "score": score, "decision": decision}

