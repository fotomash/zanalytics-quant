"""
Enhanced Risk Enforcer - Scientific Position Sizing with Behavioral Psychology
"""
import os
import json
import redis
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import yaml
import numpy as np

# Safe MT5 import
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    mt5 = None

class RiskPhase(Enum):
    LOW_EQUITY = "low_equity"
    STABLE = "stable"
    NEW_HIGH = "new_high"
    RECOVERY = "recovery"

class RiskDecision(Enum):
    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"

@dataclass
class RiskLimits:
    daily_loss_limit: float = 0.03  # 3% buffer under 5% prop limit
    per_trade_risk: float = 0.005   # 0.5% starting risk
    max_trades_per_day: int = 5
    consecutive_loss_limit: int = 2
    cooldown_minutes: int = 15

@dataclass
class AccountState:
    current_equity: float
    starting_equity: float
    peak_equity: float
    daily_pnl: float
    trades_today: int
    consecutive_losses: int
    last_trade_time: Optional[datetime] = None

class EnhancedRiskEnforcer:
    """Scientific Risk Enforcer with Behavioral Psychology Integration"""
    
    def __init__(self, config_path: str = "pulse_config.yaml"):
        self.config = self._load_config(config_path)
        self.logger = logging.getLogger(__name__)
        
        # Redis connection with error handling
        try:
            self.redis_client = redis.Redis(
                host=os.getenv('REDIS_HOST', 'redis'),
                port=int(os.getenv('REDIS_PORT', 6379)),
                decode_responses=True,
                socket_timeout=2.0,
                socket_connect_timeout=2.0
            )
            self.redis_client.ping()
            self.redis_available = True
        except Exception as e:
            self.logger.warning(f"Redis unavailable: {e}")
            self.redis_available = False
            self.redis_client = None
        
        # MT5 lazy initialization
        self.mt5_connected = False
        self.mt5_available = MT5_AVAILABLE
        
        # Risk limits by phase with scientific adjustments
        self.risk_limits = {
            RiskPhase.LOW_EQUITY: RiskLimits(per_trade_risk=0.003, max_trades_per_day=2),  # Conservative
            RiskPhase.STABLE: RiskLimits(per_trade_risk=0.005, max_trades_per_day=3),       # Moderate
            RiskPhase.NEW_HIGH: RiskLimits(per_trade_risk=0.007, max_trades_per_day=4),     # Growth
            RiskPhase.RECOVERY: RiskLimits(per_trade_risk=0.004, max_trades_per_day=2)      # Recovery
        }
    
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration with error handling"""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            self.logger.warning(f"Config file {config_path} not found, using defaults")
            return {}
        except Exception as e:
            self.logger.error(f"Error loading config: {e}")
            return {}
    
    def _init_mt5(self) -> bool:
        """Initialize MT5 connection safely"""
        if not self.mt5_available:
            self.logger.info("MT5 not available, using mock mode")
            return False
        
        try:
            if not mt5.initialize():
                self.logger.warning("MT5 initialize failed")
                return False
            
            # Only attempt login if credentials provided
            login = os.getenv('MT5_LOGIN')
            password = os.getenv('MT5_PASSWORD')
            server = os.getenv('MT5_SERVER')
            
            if login and password and server:
                success = mt5.login(login=int(login), password=password, server=server)
                if success:
                    self.logger.info("MT5 login successful")
                    return True
                else:
                    self.logger.warning("MT5 login failed")
                    return False
            else:
                self.logger.info("MT5 credentials not provided, terminal initialized without login")
                return True
                
        except Exception as e:
            self.logger.error(f"MT5 initialization error: {e}")
            return False
    
    def _ensure_mt5(self):
        """Ensure MT5 connection with lazy initialization"""
        if not self.mt5_connected and self.mt5_available:
            self.mt5_connected = self._init_mt5()
    
    def get_current_account_state(self) -> AccountState:
        """Get current account state with fallback to mock data"""
        self._ensure_mt5()
        
        if not self.mt5_connected:
            # Return safe mock data for testing/development
            return AccountState(
                current_equity=10000.0,
                starting_equity=10000.0,
                peak_equity=10000.0,
                daily_pnl=0.0,
                trades_today=0,
                consecutive_losses=0,
                last_trade_time=None
            )
        
        try:
            account_info = mt5.account_info()
            if not account_info:
                raise RuntimeError("MT5 account_info unavailable")
            
            daily_stats = self._get_daily_stats()
            
            return AccountState(
                current_equity=account_info.equity,
                starting_equity=account_info.balance,
                peak_equity=max(account_info.equity, account_info.balance),
                daily_pnl=account_info.profit,
                trades_today=daily_stats.get('trades_today', 0),
                consecutive_losses=daily_stats.get('consecutive_losses', 0),
                last_trade_time=daily_stats.get('last_trade_time')
            )
        except Exception as e:
            self.logger.error(f"Error getting account state: {e}")
            # Return safe fallback
            return AccountState(10000.0, 10000.0, 10000.0, 0.0, 0, 0, None)
    
    def _get_daily_stats(self) -> Dict:
        """Get daily trading statistics with error handling"""
        if not self.mt5_connected:
            return {'trades_today': 0, 'consecutive_losses': 0, 'last_trade_time': None}
        
        try:
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = datetime.now()
            
            deals = mt5.history_deals_get(start_date, end_date)
            if not deals:
                return {'trades_today': 0, 'consecutive_losses': 0, 'last_trade_time': None}
            
            # Calculate consecutive losses
            consecutive_losses = 0
            last_trade_time = None
            
            for deal in reversed(deals):
                if deal.profit < 0:
                    consecutive_losses += 1
                    if last_trade_time is None:
                        last_trade_time = datetime.fromtimestamp(deal.time)
                else:
                    break
            
            return {
                'trades_today': len(deals),
                'consecutive_losses': consecutive_losses,
                'last_trade_time': last_trade_time
            }
        except Exception as e:
            self.logger.error(f"Error getting daily stats: {e}")
            return {'trades_today': 0, 'consecutive_losses': 0, 'last_trade_time': None}
    
    def determine_risk_phase(self, account_state: AccountState) -> RiskPhase:
        """Determine current risk phase based on account performance"""
        try:
            equity_ratio = account_state.current_equity / account_state.starting_equity
            peak_ratio = account_state.current_equity / account_state.peak_equity
            
            if equity_ratio < 1.02:  # Less than 2% gain
                return RiskPhase.LOW_EQUITY
            elif account_state.current_equity > account_state.peak_equity:
                return RiskPhase.NEW_HIGH
            elif peak_ratio >= 0.98:  # Within 2% of peak
                return RiskPhase.STABLE
            else:
                return RiskPhase.RECOVERY
        except (ZeroDivisionError, TypeError):
            return RiskPhase.LOW_EQUITY
    
    def calculate_dynamic_position_size(self, 
                                      account_state: AccountState,
                                      signal_confidence: float,
                                      stop_loss_pips: float,
                                      pip_value: float,
                                      max_daily_risk_pct: float = 2.0,
                                      anticipated_trades: int = 3) -> Dict:
        """
        Scientific position sizing with behavioral psychology integration
        
        Args:
            account_state: Current account state
            signal_confidence: Confluence score (0-100)
            stop_loss_pips: Stop loss distance in pips
            pip_value: Value per pip
            max_daily_risk_pct: Maximum daily risk percentage
            anticipated_trades: Number of trades planned for the day
        """
        
        # Base risk calculation
        daily_risk_amount = account_state.current_equity * (max_daily_risk_pct / 100)
        per_trade_risk = daily_risk_amount / anticipated_trades
        
        # Confidence-based adjustment (psychological factor)
        confidence_multiplier = min(1.0, signal_confidence / 100)  # Cap at 100%
        
        # Risk phase adjustment (scientific factor)
        risk_phase = self.determine_risk_phase(account_state)
        phase_multiplier = {
            RiskPhase.LOW_EQUITY: 0.7,   # Reduce risk in low equity phase
            RiskPhase.STABLE: 1.0,       # Normal risk
            RiskPhase.NEW_HIGH: 1.2,     # Increase risk in new high phase
            RiskPhase.RECOVERY: 0.6      # Conservative in recovery
        }.get(risk_phase, 1.0)
        
        # Behavioral adjustment (psychological factor)
        behavioral_multiplier = 1.0
        if account_state.consecutive_losses >= 2:
            behavioral_multiplier = 0.5  # Reduce risk after consecutive losses
        elif account_state.trades_today >= anticipated_trades * 0.8:
            behavioral_multiplier = 0.8  # Reduce risk near trade limit
        
        # Calculate final position size
        adjusted_risk = per_trade_risk * confidence_multiplier * phase_multiplier * behavioral_multiplier
        
        if stop_loss_pips > 0 and pip_value > 0:
            position_size = round(adjusted_risk / (stop_loss_pips * pip_value), 2)
        else:
            position_size = 0
        
        return {
            "position_size": position_size,
            "risk_amount": adjusted_risk,
            "confidence_multiplier": confidence_multiplier,
            "phase_multiplier": phase_multiplier,
            "behavioral_multiplier": behavioral_multiplier,
            "effective_multiplier": confidence_multiplier * phase_multiplier * behavioral_multiplier,
            "risk_phase": risk_phase.value
        }
    
    def check_behavioral_patterns(self, account_state: AccountState, signal: Dict) -> Tuple[RiskDecision, str]:
        """Check for behavioral trading patterns with psychological insights"""
        flags = []
        
        try:
            # Overconfidence check (high confluence score after wins)
            if (signal.get('confluence_score', 0) > 85 and 
                account_state.consecutive_losses == 0 and 
                account_state.trades_today >= 3):
                flags.append("overconfidence_risk")
            
            # Revenge trading check
            if (account_state.consecutive_losses >= 2 and 
                account_state.last_trade_time and
                datetime.now() - account_state.last_trade_time < timedelta(minutes=30)):
                flags.append("revenge_trading_risk")
            
            # Disposition effect check
            if (account_state.daily_pnl < 0 and 
                signal.get('risk_reward', 0) < 1.5):
                flags.append("disposition_effect_risk")
            
            # Fatigue check
            if account_state.trades_today >= 5:
                flags.append("trading_fatigue")
            
            if flags:
                return RiskDecision.WARN, f"Behavioral flags: {', '.join(flags)}"
            
            return RiskDecision.ALLOW, "No behavioral red flags detected"
            
        except Exception as e:
            self.logger.error(f"Error in behavioral check: {e}")
            return RiskDecision.WARN, "Behavioral check error"

    def check(self, ts: str, symbol: str, score: float, features: Dict | None = None) -> Dict:
        """Compatibility wrapper for legacy interface"""
        if features and features.get('news_active'):
            return {'status': 'blocked', 'reason': ['News event active'], 'raw': {}}

        signal = {'symbol': symbol, 'confluence_score': score}
        if features:
            signal.update(features)

        result = self.evaluate_trade_request(signal)
        status_map = {'allow': 'allowed', 'warn': 'warned', 'block': 'blocked'}
        return {
            'status': status_map.get(result['decision'], 'blocked'),
            'reason': result.get('reasons', []),
            'raw': result
        }

    def evaluate_trade_request(self, signal: Dict, account_state: Optional[AccountState] = None) -> Dict:
        """Comprehensive trade evaluation with scientific position sizing"""
        try:
            if account_state is None:
                account_state = self.get_current_account_state()
            
            risk_phase = self.determine_risk_phase(account_state)
            limits = self.risk_limits[risk_phase]
            
            # Run all risk checks
            checks = {
                "daily_loss": self._check_daily_loss_limit(account_state, limits),
                "trade_frequency": self._check_trade_frequency(account_state, limits),
                "behavioral": self.check_behavioral_patterns(account_state, signal),
                "cooldown": self._check_cooldown_period(account_state, limits)
            }
            
            # Determine overall decision
            decisions = [check[0] for check in checks.values()]
            reasons = [check[1] for check in checks.values() if check[1]]
            
            if RiskDecision.BLOCK in decisions:
                overall_decision = RiskDecision.BLOCK
            elif RiskDecision.WARN in decisions:
                overall_decision = RiskDecision.WARN
            else:
                overall_decision = RiskDecision.ALLOW
            
            # Calculate position size if allowed
            position_sizing = {}
            if overall_decision != RiskDecision.BLOCK:
                # Get user-defined parameters from signal or defaults
                max_daily_risk = signal.get('max_daily_risk_pct', 2.0)
                anticipated_trades = signal.get('anticipated_trades', 3)
                stop_loss_pips = signal.get('stop_loss_pips', 20)
                pip_value = signal.get('pip_value', 1.0)
                confluence_score = signal.get('confluence_score', 75)
                
                position_sizing = self.calculate_dynamic_position_size(
                    account_state,
                    confluence_score,
                    stop_loss_pips,
                    pip_value,
                    max_daily_risk,
                    anticipated_trades
                )
            
            result = {
                "decision": overall_decision.value,
                "allowed": overall_decision == RiskDecision.ALLOW,
                "risk_phase": risk_phase.value,
                "position_sizing": position_sizing,
                "position_size": position_sizing.get("position_size", 0),
                "reasons": reasons,
                "behavioral_flags": [r for r in reasons if any(flag in r.lower() for flag in ['overconfidence', 'revenge', 'disposition', 'fatigue'])],
                "risk_level": "critical" if overall_decision == RiskDecision.BLOCK else "medium" if overall_decision == RiskDecision.WARN else "low",
                "remaining_budget": max(0, limits.daily_loss_limit - abs(account_state.daily_pnl / account_state.starting_equity)),
                "trades_remaining": max(0, limits.max_trades_per_day - account_state.trades_today),
                "timestamp": datetime.now().isoformat()
            }
            
            # Log decision safely
            self._log_decision(signal, account_state, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in trade evaluation: {e}")
            return {
                "decision": "block",
                "allowed": False,
                "risk_phase": "unknown",
                "position_size": 0,
                "reasons": [f"System error: {str(e)}"],
                "behavioral_flags": [],
                "risk_level": "critical",
                "remaining_budget": 0,
                "trades_remaining": 0,
                "timestamp": datetime.now().isoformat()
            }
    
    def _check_daily_loss_limit(self, account_state: AccountState, limits: RiskLimits) -> Tuple[RiskDecision, str]:
        """Check if daily loss limit would be breached"""
        try:
            daily_loss_pct = abs(account_state.daily_pnl) / account_state.starting_equity
            
            if daily_loss_pct >= limits.daily_loss_limit:
                return RiskDecision.BLOCK, f"Daily loss limit reached: {daily_loss_pct:.2%}"
            elif daily_loss_pct >= 0.02:  # 2% warning threshold
                return RiskDecision.WARN, f"Approaching daily loss limit: {daily_loss_pct:.2%}"
            
            return RiskDecision.ALLOW, "Daily loss within limits"
        except (ZeroDivisionError, TypeError):
            return RiskDecision.WARN, "Unable to calculate daily loss"
    
    def _check_trade_frequency(self, account_state: AccountState, limits: RiskLimits) -> Tuple[RiskDecision, str]:
        """Check trade frequency limits"""
        if account_state.trades_today >= limits.max_trades_per_day:
            return RiskDecision.BLOCK, f"Max trades per day reached: {account_state.trades_today}/{limits.max_trades_per_day}"
        
        return RiskDecision.ALLOW, "Trade frequency within limits"
    
    def _check_cooldown_period(self, account_state: AccountState, limits: RiskLimits) -> Tuple[RiskDecision, str]:
        """Check cooling off period after losses"""
        if (account_state.consecutive_losses >= limits.consecutive_loss_limit and 
            account_state.last_trade_time and 
            datetime.now() - account_state.last_trade_time < timedelta(minutes=limits.cooldown_minutes)):
            return RiskDecision.BLOCK, f"Cooling off period active: {limits.cooldown_minutes} minutes after {account_state.consecutive_losses} losses"
        
        return RiskDecision.ALLOW, "No cooldown active"
    
    def _log_decision(self, signal: Dict, account_state: AccountState, result: Dict):
        """Log risk decision with error handling"""
        if not self.redis_available:
            return
        
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "symbol": signal.get("symbol"),
                "confluence_score": signal.get("confluence_score"),
                "decision": result["decision"],
                "risk_phase": result["risk_phase"],
                "account_equity": account_state.current_equity,
                "daily_pnl": account_state.daily_pnl,
                "trades_today": account_state.trades_today,
                "position_size": result.get("position_size", 0),
                "reasons": result["reasons"]
            }
            
            # Store in Redis with expiration
            key = f"risk_log:{datetime.now().strftime('%Y%m%d')}"
            self.redis_client.lpush(key, json.dumps(log_entry))
            self.redis_client.expire(key, 86400 * 7)  # Keep for 7 days
            
        except Exception as e:
            self.logger.error(f"Error logging decision: {e}")
    
    def get_risk_status(self, account_state: Optional[AccountState] = None) -> Dict:
        """Get current risk status for dashboard"""
        try:
            if account_state is None:
                account_state = self.get_current_account_state()
            
            risk_phase = self.determine_risk_phase(account_state)
            limits = self.risk_limits[risk_phase]
            
            daily_loss_pct = abs(account_state.daily_pnl) / account_state.starting_equity
            risk_used_pct = (daily_loss_pct / limits.daily_loss_limit) * 100
            
            return {
                "risk_phase": risk_phase.value,
                "daily_loss_pct": daily_loss_pct,
                "daily_risk_used": risk_used_pct,
                "risk_used_pct": min(risk_used_pct, 100),
                "risk_remaining_pct": max(100 - risk_used_pct, 0),
                "trades_used": account_state.trades_today,
                "trades_remaining": max(limits.max_trades_per_day - account_state.trades_today, 0),
                "trades_left": max(limits.max_trades_per_day - account_state.trades_today, 0),
                "max_trades": limits.max_trades_per_day,
                "per_trade_risk": limits.per_trade_risk,
                "consecutive_losses": account_state.consecutive_losses,
                "status": risk_phase.value.replace('_', ' ').title(),
                "warnings": self._get_current_warnings(account_state, limits)
            }
        except Exception as e:
            self.logger.error(f"Error getting risk status: {e}")
            return {
                "risk_phase": "unknown",
                "daily_loss_pct": 0,
                "daily_risk_used": 0,
                "risk_used_pct": 0,
                "risk_remaining_pct": 100,
                "trades_used": 0,
                "trades_remaining": 5,
                "trades_left": 5,
                "max_trades": 5,
                "per_trade_risk": 0.005,
                "consecutive_losses": 0,
                "status": "Unknown",
                "warnings": ["System error"]
            }
    
    def _get_current_warnings(self, account_state: AccountState, limits: RiskLimits) -> List[str]:
        """Get current risk warnings"""
        warnings = []
        
        try:
            daily_loss_pct = abs(account_state.daily_pnl) / account_state.starting_equity
            
            if daily_loss_pct > 0.02:
                warnings.append("Approaching daily loss limit")
            
            if account_state.consecutive_losses >= 2:
                warnings.append("Multiple consecutive losses")
            
            if account_state.trades_today >= limits.max_trades_per_day * 0.8:
                warnings.append("Approaching trade limit")
                
        except Exception:
            warnings.append("Unable to calculate warnings")
        
        return warnings

# Factory function for integration
def create_risk_enforcer() -> EnhancedRiskEnforcer:
    """Factory function to create risk enforcer"""
    return EnhancedRiskEnforcer()

# Backwards compatibility alias
RiskEnforcer = EnhancedRiskEnforcer
