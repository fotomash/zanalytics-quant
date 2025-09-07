"""
RiskEnforcer - Behavioral Protection System
Enforces trading discipline and risk management rules
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import logging

logger = logging.getLogger(__name__)

try:
    # Optional policies loader (Django app path); degrade gracefully if unavailable
    from backend.django.app.utils.policies import load_policies  # type: ignore
except Exception:  # pragma: no cover
    def load_policies():  # fallback
        return {}

class RiskEnforcer:
    """
    Enforces risk management rules and behavioral safeguards.
    Acts as the "seatbelt" for trading decisions.
    """
    
    def __init__(self, config: Dict = None):
        # Risk limits (configurable)
        self.limits = config.get('limits', {
            'daily_loss_limit': 500,        # USD
            'daily_loss_percent': 0.03,     # 3% (buffer before 5% prop limit)
            'max_trades_per_day': 5,
            'max_position_size': 0.02,      # 2% max risk per trade
            'cooling_period_minutes': 15,
            'revenge_trade_window': 30,     # minutes
            'max_consecutive_losses': 3
        }) if config else self._default_limits()
        
        # Current state
        self.daily_stats = {
            'date': datetime.now().date(),
            'trades_count': 0,
            'total_pnl': 0,
            'losses_count': 0,
            'consecutive_losses': 0,
            'last_loss_time': None,
            'cooling_until': None,
            'violations': []
        }

        # Trading state for behavioral checks
        self.state = {
            'consecutive_wins': 0,
            'confidence_level': 0.0
        }
        
        # Behavioral tracking
        self.behavioral_flags = {
            'revenge_trading': False,
            'overconfidence': False,
            'fatigue': False,
            'tilt': False
        }
        
    def _default_limits(self) -> Dict:
        """Default risk limits"""
        return {
            'daily_loss_limit': 500,
            'daily_loss_percent': 0.03,
            'max_trades_per_day': 5,
            'max_position_size': 0.02,
            'cooling_period_minutes': 15,
            'revenge_trade_window': 30,
            'max_consecutive_losses': 3
        }

class EnhancedRiskEnforcer:
    """
    Adapter used by pulse_api to expose a richer, queryable risk surface.

    It wraps RiskEnforcer and adds:
      - get_risk_status(): summarized metrics for tiles
      - evaluate_trade_request(payload): decision contract for /risk/check
    """

    def __init__(self):
        # Load policy snapshot if available
        policies = load_policies() or {}
        # Map a few known policy fields into RiskEnforcer limits
        limits = {
            'daily_loss_limit': None,  # USD optional
            'daily_loss_percent': None,
            'max_trades_per_day': None,
            'max_position_size': None,
            'cooling_period_minutes': None,
        }
        # Pull dynamic values if present
        risk_pol = policies if isinstance(policies, dict) else {}
        # Support both naming conventions
        dl_pct = (
            risk_pol.get('daily_loss_cap_pct')
            or risk_pol.get('risk', {}).get('max_daily_loss_pct')
        )
        pt_max = (
            risk_pol.get('per_trade_risk_pct_max')
            or risk_pol.get('risk', {}).get('max_single_trade_loss_pct')
        )
        max_trades = (
            risk_pol.get('max_trades_per_day')
            or risk_pol.get('risk', {}).get('max_daily_trades')
        )
        cooling = (
            risk_pol.get('cool_off', {}).get('minutes')
        )
        # Build effective config
        effective = {}
        if dl_pct is not None:
            effective['daily_loss_percent'] = float(dl_pct) / 100.0 if dl_pct > 1 else float(dl_pct)
        if pt_max is not None:
            effective['max_position_size'] = float(pt_max) / 100.0 if pt_max > 1 else float(pt_max)
        if max_trades is not None:
            effective['max_trades_per_day'] = int(max_trades)
        if cooling is not None:
            effective['cooling_period_minutes'] = int(cooling)

        self.core = RiskEnforcer(config={'limits': effective} if effective else None)

    # --- Public API expected by pulse_api.views ---
    def get_risk_status(self) -> Dict:
        ds = self.core.daily_stats
        lim = self.core.limits
        # Compute daily risk used as % of limit if USD cap present; else use percent cap
        used_pct = 0.0
        remaining_pct = 100.0
        try:
            if lim.get('daily_loss_limit'):
                used = max(0.0, abs(float(ds.get('total_pnl', 0.0))))
                cap = float(lim['daily_loss_limit'])
                used_pct = min(100.0, (used / cap) * 100.0) if cap > 0 else 0.0
                remaining_pct = max(0.0, 100.0 - used_pct)
            elif lim.get('daily_loss_percent'):
                # Percent-based cap: approximate used% from pnl vs cap% of equity baseline (unknown here)
                # Without equity context, expose remaining as 100 and let UI compute vs SOD.
                remaining_pct = 100.0
        except Exception:
            remaining_pct = 100.0

        warnings: List[str] = []
        if ds.get('cooling_until') and ds['cooling_until'] > datetime.now():
            warnings.append('Cooling period active')
        if ds.get('consecutive_losses', 0) >= self.core.limits.get('max_consecutive_losses', 3):
            warnings.append('Loss streak threshold reached')

        status = 'OK'
        if warnings:
            status = 'Warning'

        return {
            'risk_remaining_pct': remaining_pct,
            'trades_remaining': max(0, int(self.core.limits.get('max_trades_per_day', 5)) - int(ds.get('trades_count', 0))),
            'status': status,
            'warnings': warnings,
            'daily_risk_used': used_pct,
        }

    def evaluate_trade_request(self, payload: Dict) -> Dict:
        """Map incoming payload to RiskEnforcer signal and return decision."""
        # Normalize incoming risk/size % → fraction
        size_pct = payload.get('risk_pct') or payload.get('size_pct') or payload.get('size') or 0
        try:
            size = float(size_pct)
            if size > 1.0:
                size = size / 100.0
        except Exception:
            size = 0.0

        signal = {
            'size': size,
            'score': payload.get('score', 0),
            'symbol': payload.get('symbol', ''),
            'side': payload.get('side', ''),
            'planned': bool(payload.get('planned', False)),
        }
        allowed, warnings, details = self.core.allow(signal)
        decision = {
            'decision': 'allow' if allowed else 'block',
            'reasons': warnings or ['OK'],
            'trades_remaining': details.get('trades_remaining', 0),
            'daily_risk_used': self.get_risk_status().get('daily_risk_used', 0),
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        return decision
    
    def allow(self, signal: Dict) -> Tuple[bool, List[str], Dict]:
        """
        Main enforcement method - checks if a trade should be allowed.
        
        Args:
            signal: Trade signal with score, size, etc.
            
        Returns:
            Tuple of (allowed, warnings, details)
        """
        allowed = True
        warnings = []
        details = {}
        
        # Check daily loss limit
        loss_check = self._check_daily_loss()
        if not loss_check['allowed']:
            allowed = False
            warnings.append(loss_check['reason'])
        if loss_check.get('flag'):
            self.daily_stats['violations'].append(loss_check['flag'])
            
        # Check trade count
        count_check = self._check_trade_count()
        if not count_check['allowed']:
            allowed = False
            warnings.append(count_check['reason'])
        elif count_check.get('warning'):
            warnings.append(count_check['warning'])
            
        # Check cooling period
        cooling_check = self._check_cooling_period()
        if not cooling_check['allowed']:
            allowed = False
            warnings.append(cooling_check['reason'])
            
        # Check position size
        size_check = self._check_position_size(signal.get('size', 0))
        if not size_check['allowed']:
            allowed = False
            warnings.append(size_check['reason'])
            
        # Check behavioral patterns
        behavioral_check = self._check_behavioral_patterns()
        if behavioral_check['warnings']:
            warnings.extend(behavioral_check['warnings'])
            
        # Check for revenge trading
        revenge_check = self._check_revenge_trading()
        if revenge_check['detected']:
            warnings.append('⚠️ Revenge trading pattern detected')
            self.behavioral_flags['revenge_trading'] = True
            
        # Check for overconfidence
        confidence_check = self._check_overconfidence()
        if confidence_check['detected']:
            warnings.append('⚠️ Overconfidence detected - consider smaller size')
            self.behavioral_flags['overconfidence'] = True
            
        # Compile details
        details = {
            'trades_remaining': self.limits['max_trades_per_day'] - self.daily_stats['trades_count'],
            'loss_buffer': self.limits['daily_loss_limit'] - abs(self.daily_stats['total_pnl']),
            'behavioral_score': self._calculate_behavioral_score(),
            'risk_level': self._calculate_risk_level(),
            'flags': self.behavioral_flags
        }

        return allowed, warnings, details

    def evaluate_signal(self, signal: Dict) -> Dict:
        """Convenience wrapper returning structured decision data."""
        allowed, warnings, details = self.allow(signal)
        flags: List[str] = []

        # Include violation flags
        flags.extend(self.daily_stats.get('violations', []))

        # Include behavioral flags
        for key, val in details.get('flags', {}).items():
            if val:
                if key == 'overconfidence':
                    flags.append('OVERCONFIDENCE_ALERT')
                else:
                    flags.append(key.upper())

        return {
            'approved': allowed,
            'reason': warnings[0] if warnings else 'APPROVED',
            'risk_score': details.get('behavioral_score', 0),
            'flags': flags
        }
    
    def _check_daily_loss(self) -> Dict:
        """Check if daily loss limit is exceeded"""
        if self.daily_stats['total_pnl'] <= -self.limits['daily_loss_limit']:
            return {
                'allowed': False,
                'reason': '🔴 Daily loss limit reached. No more trades today.',
                'flag': 'DAILY_LIMIT_REACHED'
            }
        
        # Warning if close to limit
        if self.daily_stats['total_pnl'] <= -self.limits['daily_loss_limit'] * 0.8:
            return {
                'allowed': True,
                'warning': '⚠️ Approaching daily loss limit (80% reached)'
            }
            
        return {'allowed': True}
    
    def _check_trade_count(self) -> Dict:
        """Check if max trades per day exceeded"""
        if self.daily_stats['trades_count'] >= self.limits['max_trades_per_day']:
            return {
                'allowed': False,
                'reason': '🔴 Maximum trades per day reached.'
            }
            
        if self.daily_stats['trades_count'] == self.limits['max_trades_per_day'] - 1:
            return {
                'allowed': True,
                'warning': '⚠️ This is your last trade for today'
            }
            
        return {'allowed': True}
    
    def _check_cooling_period(self) -> Dict:
        """Check if cooling period is active"""
        if self.daily_stats['cooling_until']:
            if datetime.now() < self.daily_stats['cooling_until']:
                remaining = (self.daily_stats['cooling_until'] - datetime.now()).seconds // 60
                return {
                    'allowed': False,
                    'reason': f'❄️ Cooling period active. {remaining} minutes remaining.'
                }
            else:
                # Cooling period expired
                self.daily_stats['cooling_until'] = None
                
        return {'allowed': True}
    
    def _check_position_size(self, size: float) -> Dict:
        """Check if position size is within limits"""
        if size > self.limits['max_position_size']:
            return {
                'allowed': False,
                'reason': f'🔴 Position size {size:.1%} exceeds maximum {self.limits["max_position_size"]:.1%}'
            }
        return {'allowed': True}
    
    def _check_behavioral_patterns(self) -> Dict:
        """Check for problematic behavioral patterns"""
        warnings = []
        
        # Check time of day (fatigue)
        current_hour = datetime.now().hour
        if current_hour >= 22 or current_hour <= 6:
            warnings.append('🌙 Late night trading - higher risk of errors')
            self.behavioral_flags['fatigue'] = True
            
        # Check consecutive losses
        if self.daily_stats['consecutive_losses'] >= 2:
            warnings.append(f'📉 {self.daily_stats["consecutive_losses"]} consecutive losses - consider a break')
            
        # Check rapid trading
        if self._is_rapid_trading():
            warnings.append('⚡ Rapid trading detected - slow down')
            
        return {'warnings': warnings}
    
    def _check_revenge_trading(self) -> Dict:
        """Detect revenge trading patterns"""
        if not self.daily_stats['last_loss_time']:
            return {'detected': False}
            
        time_since_loss = datetime.now() - self.daily_stats['last_loss_time']
        
        if time_since_loss.seconds < self.limits['revenge_trade_window'] * 60:
            if self.daily_stats['consecutive_losses'] > 0:
                return {
                    'detected': True,
                    'confidence': 0.8,
                    'reason': 'Quick re-entry after loss'
                }
                
        return {'detected': False}
    
    def _check_overconfidence(self) -> Dict:
        """Detect overconfidence patterns"""
        if self.state.get('consecutive_wins', 0) >= 3 or self.state.get('confidence_level', 0) > 0.8:
            return {
                'detected': True,
                'confidence': self.state.get('confidence_level', 0),
                'reason': 'Winning streak / high confidence'
            }
        if self.daily_stats['trades_count'] >= 4:
            return {
                'detected': True,
                'confidence': 0.7,
                'reason': 'High trade frequency'
            }
        return {'detected': False}
    
    def _is_rapid_trading(self) -> bool:
        """Check if trading too rapidly"""
        # Would check timestamps of recent trades
        # Simplified for now
        return False
    
    def _calculate_behavioral_score(self) -> int:
        """Calculate overall behavioral score 0-100"""
        score = 100
        
        # Deduct for flags
        if self.behavioral_flags['revenge_trading']:
            score -= 30
        if self.behavioral_flags['overconfidence']:
            score -= 20
        if self.behavioral_flags['fatigue']:
            score -= 15
        if self.behavioral_flags['tilt']:
            score -= 25
            
        # Deduct for violations
        score -= len(self.daily_stats['violations']) * 10
        
        return max(0, score)
    
    def _calculate_risk_level(self) -> str:
        """Calculate current risk level"""
        score = self._calculate_behavioral_score()

        if score >= 80:
            return 'low'
        elif score >= 60:
            return 'medium'
        elif score >= 40:
            return 'high'
        else:
            return 'critical'

    def get_behavioral_report(self) -> Dict:
        """Return current behavioral state for external reporting."""
        state = {
            'confidence_level': self.state.get('confidence_level', 0.0),
            'daily_pnl_percent': self.daily_stats.get('total_pnl', 0.0),
            'trades_today': self.daily_stats.get('trades_count', 0),
            'emotional_state': 'neutral'
        }
        recommendations: List[str] = []

        if self.behavioral_flags.get('overconfidence'):
            state['emotional_state'] = 'confident'
            recommendations.append('Reduce position size to manage confidence')
        elif self.behavioral_flags.get('revenge_trading'):
            state['emotional_state'] = 'anxious'
            recommendations.append('Pause trading to avoid revenge trades')

        return {
            'current_state': state,
            'recommendations': recommendations
        }
    
    def update_trade_result(self, result: Dict):
        """Update stats after a trade completes"""
        self.daily_stats['trades_count'] += 1
        self.daily_stats['total_pnl'] += result.get('pnl', 0)
        
        if result.get('pnl', 0) < 0:
            self.daily_stats['losses_count'] += 1
            self.daily_stats['consecutive_losses'] += 1
            self.daily_stats['last_loss_time'] = datetime.now()
            
            # Trigger cooling period after significant loss
            if abs(result.get('pnl', 0)) > 100:
                self.daily_stats['cooling_until'] = (
                    datetime.now() + timedelta(minutes=self.limits['cooling_period_minutes'])
                )
        else:
            self.daily_stats['consecutive_losses'] = 0
            
    def reset_daily_stats(self):
        """Reset daily statistics"""
        self.daily_stats = {
            'date': datetime.now().date(),
            'trades_count': 0,
            'total_pnl': 0,
            'losses_count': 0,
            'consecutive_losses': 0,
            'last_loss_time': None,
            'cooling_until': None,
            'violations': []
        }
        
        self.behavioral_flags = {
            'revenge_trading': False,
            'overconfidence': False,
            'fatigue': False,
            'tilt': False
        }
