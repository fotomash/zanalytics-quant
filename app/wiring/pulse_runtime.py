from __future__ import annotations
import os, json, time, logging
from pathlib import Path
from typing import Dict, Any
from mt5_bridge_production import MT5Bridge              # ← from your file
from pulse_kernel import PulseKernel                     # ← orchestrator
from datetime import datetime

logger = logging.getLogger(__name__)

JOURNAL_PATH = os.getenv("PULSE_JOURNAL_PATH", "signal_journal.json")

class PulseRuntime:
    """Runtime singleton wiring MT5 ↔ Kernel ↔ Journal."""
    def __init__(self) -> None:
        self.mt5 = MT5Bridge(
            account=int(os.getenv("MT5_ACCOUNT", "0")) or None,
            password=os.getenv("MT5_PASSWORD") or None,
            server=os.getenv("MT5_SERVER") or None,
        )
        cfg_path = os.getenv("PULSE_CONFIG", "pulse_config.yaml")
        if not os.path.exists(cfg_path):
            logger.warning("Pulse config file %s not found; using defaults", cfg_path)
        self.kernel = PulseKernel(config_path=cfg_path)
        self.connected = False

    def connect_mt5(self) -> bool:
        if self.connected:
            return True
        self.connected = self.mt5.connect()
        return self.connected

    # ---------- DATA SOURCES ----------
    def trade_history_df(self, days_back: int = 30):
        if not self.connect_mt5():
            return None
        return self.mt5.get_real_trade_history(days_back=days_back)

    def behavioral_report(self) -> Dict[str, Any]:
        if not self.connect_mt5():
            return {"error": "MT5 not connected"}
        return self.mt5.get_behavioral_report()

    def weekly_review(self) -> Dict[str, Any]:
        if not self.connect_mt5():
            return {"error": "MT5 not connected"}
        return self.mt5.generate_weekly_review()

    def confluence_validation_df(self):
        if not self.connect_mt5():
            return None
        return self.mt5.get_confluence_validation(journal_path=JOURNAL_PATH)

    # ---------- LIVE SCORING / RISK ----------
    def score_symbol_snapshot(self, symbol: str, price: float) -> Dict[str, Any]:
        """
        Minimal example of routing a 'tick' to the kernel and getting back
        both confluence and risk gating for the decision surface.
        """
        tick = {
            "timestamp": datetime.utcnow().isoformat(),
            "symbol": symbol,
            "bid": price,
            "ask": price,
            "mid": price,
        }
        # Kernel’s process_frame/on_frame may be async in your tree.
        # Keep a sync shim for Streamlit.
        if hasattr(self.kernel, "on_frame"):
            import asyncio
            return asyncio.run(self.kernel.on_frame(tick))
        if hasattr(self.kernel, "process_frame"):
            return self.kernel.process_frame(tick)
        # Fallback:
        score = 0
        reasons = ["Kernel not wired"]
        return {"action": "none", "confidence": score, "reasons": reasons}

    # ---------- JOURNAL ----------
    def sync_journal(self) -> int:
        if not self.connect_mt5():
            return 0
        return self.mt5.sync_to_pulse_journal(journal_path=JOURNAL_PATH)

runtime = PulseRuntime()
