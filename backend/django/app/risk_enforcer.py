"""
App-local EnhancedRiskEnforcer used by pulse_api.

Implements the minimal API expected by pulse_api:
  - get_risk_status()
  - evaluate_trade_request(payload)

Loads optional policy snapshot via app.utils.policies.load_policies.
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, Any, List

try:
    from app.utils.policies import load_policies  # type: ignore
except Exception:  # pragma: no cover
    def load_policies():  # fallback
        return {}


class _Core:
    """Tiny core state holder with simple limits + counters."""

    def __init__(self, limits: Dict[str, Any] | None = None) -> None:
        self.limits = limits or {
            'daily_loss_limit': None,        # USD cap (optional)
            'daily_loss_percent': 0.03,      # fallback percent cap
            'max_trades_per_day': 5,
            'max_position_size': 0.02,
            'cooling_period_minutes': 15,
            'max_consecutive_losses': 3,
        }
        self.daily_stats: Dict[str, Any] = {
            'trades_count': 0,
            'total_pnl': 0.0,
            'consecutive_losses': 0,
            'cooling_until': None,
        }


class EnhancedRiskEnforcer:
    def __init__(self) -> None:
        pol = load_policies() or {}
        eff: Dict[str, Any] = {}
        # map a few fields if present
        dl_pct = pol.get('daily_loss_cap_pct') or pol.get('risk', {}).get('max_daily_loss_pct')
        if dl_pct is not None:
            eff['daily_loss_percent'] = float(dl_pct) / 100.0 if dl_pct > 1 else float(dl_pct)
        pt_max = pol.get('per_trade_risk_pct_max') or pol.get('risk', {}).get('max_single_trade_loss_pct')
        if pt_max is not None:
            eff['max_position_size'] = float(pt_max) / 100.0 if pt_max > 1 else float(pt_max)
        max_trades = pol.get('max_trades_per_day') or pol.get('risk', {}).get('max_daily_trades')
        if max_trades is not None:
            eff['max_trades_per_day'] = int(max_trades)
        cooling = pol.get('cool_off', {}).get('minutes') if isinstance(pol.get('cool_off'), dict) else None
        if cooling is not None:
            eff['cooling_period_minutes'] = int(cooling)

        self.core = _Core(eff if eff else None)

    # ---- API used by pulse_api ----
    def get_risk_status(self) -> Dict[str, Any]:
        ds = self.core.daily_stats
        lim = self.core.limits

        # used/remaining percent
        used_pct = 0.0
        remaining_pct = 100.0
        try:
            cap_usd = lim.get('daily_loss_limit')
            if cap_usd:
                used = max(0.0, abs(float(ds.get('total_pnl', 0.0))))
                cap = float(cap_usd)
                used_pct = min(100.0, (used / cap) * 100.0) if cap > 0 else 0.0
                remaining_pct = max(0.0, 100.0 - used_pct)
        except Exception:
            pass

        warnings: List[str] = []
        if ds.get('cooling_until') and ds['cooling_until'] > datetime.now():
            warnings.append('Cooling period active')
        if ds.get('consecutive_losses', 0) >= int(self.core.limits.get('max_consecutive_losses', 3)):
            warnings.append('Loss streak threshold reached')

        status = 'OK' if not warnings else 'Warning'

        return {
            'risk_remaining_pct': remaining_pct,
            'trades_remaining': max(0, int(self.core.limits.get('max_trades_per_day', 5)) - int(ds.get('trades_count', 0))),
            'status': status,
            'warnings': warnings,
            'daily_risk_used': used_pct,
        }

    def evaluate_trade_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        size_pct = payload.get('risk_pct') or payload.get('size_pct') or payload.get('size') or 0
        try:
            size = float(size_pct)
            if size > 1.0:
                size = size / 100.0
        except Exception:
            size = 0.0

        # Basic checks against caps
        allowed = True
        reasons: List[str] = []
        if size > float(self.core.limits.get('max_position_size', 0.02)):
            allowed = False
            reasons.append('Position size exceeds policy max')

        return {
            'decision': 'allow' if allowed else 'block',
            'reasons': reasons or ['OK'],
            'trades_remaining': max(0, int(self.core.limits.get('max_trades_per_day', 5)) - int(self.core.daily_stats.get('trades_count', 0))),
            'daily_risk_used': self.get_risk_status().get('daily_risk_used', 0),
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }

