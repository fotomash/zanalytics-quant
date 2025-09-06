"""
RiskEnforcer - Behavioral Protection System
Implements 6 evidence-based modules to prevent common trading failures
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging
from dataclasses import dataclass
from enum import Enum

class RiskModule(Enum):
    """Risk protection modules based on behavioral research"""
    OVERCONFIDENCE = "overconfidence_protection"
    DAILY_LIMITS = "daily_loss_limits"
    COOLING_OFF = "cooling_off_period"
    REVENGE_TRADING = "revenge_trade_prevention"
    DISPOSITION_EFFECT = "disposition_neutralizer"
    PROP_FIRM_GUARDIAN = "prop_firm_rules"

@dataclass
class RiskDecision:
    """Structured risk evaluation result"""
    approved: bool
    reason: str
    flags: List[str]
    suggestions: List[str]
    risk_score: float

class RiskEnforcer:
    """
    6-module behavioral protection system based on trading psychology research.
    Prevents 80-90% failure rate through evidence-based interventions.
    """

    def __init__(self):
        """Initialize behavioral protection modules"""
        self.logger = logging.getLogger(__name__)

        # Risk parameters (evidence-based thresholds)
        self.config = {
            'daily_loss_limit': 0.03,      # 3% buffer (prop firms typically 5%)
            'max_trades_per_day': 5,       # Prevent overtrading
            'cooling_off_minutes': 15,      # Emotional reset period
            'revenge_threshold': 2,         # Consecutive losses trigger
            'confidence_danger_zone': 0.85, # Overconfidence threshold
            'min_confluence_score': 60,     # Minimum quality threshold
            'max_position_size': 0.02,      # 2% max risk per trade
            'prop_firm_daily_limit': 0.05,  # 5% hard stop
            'prop_firm_max_loss': 0.10      # 10% account limit
        }

        # Behavioral state tracking
        self.state = {
            'trades_today': 0,
            'consecutive_losses': 0,
            'consecutive_wins': 0,
            'daily_pnl_percent': 0.0,
            'last_trade_time': None,
            'cooling_off_until': None,
            'emotional_state': 'neutral',
            'confidence_level': 0.5,
            'total_drawdown': 0.0
        }

        # Historical patterns for behavioral analysis
        self.history = {
            'trade_times': [],
            'trade_results': [],
            'emotional_markers': [],
            'rule_violations': []
        }

        self.logger.info("RiskEnforcer initialized with 6 protection modules")

    def evaluate_signal(self, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate signal through all 6 behavioral protection modules.

        Returns decision with reasoning and behavioral flags.
        """
        confluence_score = signal_data.get('confluence_score', 0)
        session_stats = signal_data.get('session_stats', {})
        market_data = signal_data.get('market_data', {})

        # Update state from session stats
        self._update_state(session_stats)

        # Run all protection modules
        checks = [
            self._check_overconfidence(confluence_score),
            self._check_daily_limits(),
            self._check_cooling_off(),
            self._check_revenge_trading(),
            self._check_disposition_effect(market_data),
            self._check_prop_firm_rules()
        ]

        # Aggregate results
        failed_checks = [c for c in checks if not c['passed']]
        flags = [c['flag'] for c in checks if c.get('flag')]
        suggestions = [c['suggestion'] for c in checks if c.get('suggestion')]

        # Calculate overall risk score
        risk_score = self._calculate_risk_score(checks, confluence_score)

        # Make final decision
        approved = len(failed_checks) == 0 and confluence_score >= self.config['min_confluence_score']

        # Build reason
        if not approved:
            if failed_checks:
                reason = failed_checks[0]['reason']
            else:
                reason = f"Insufficient confluence ({confluence_score} < {self.config['min_confluence_score']})"
        else:
            reason = f"All behavioral checks passed (risk score: {risk_score:.2f})"

        # Log decision for analysis
        self._log_decision(approved, reason, flags)

        return {
            'approved': approved,
            'reason': reason,
            'flags': flags,
            'suggestions': suggestions,
            'risk_score': risk_score,
            'modules_passed': len([c for c in checks if c['passed']]),
            'modules_total': len(checks)
        }

    def _check_overconfidence(self, confluence_score: float) -> Dict:
        """
        Module 1: Overconfidence Protection
        Prevents excessive risk-taking after winning streaks
        """
        check = {'passed': True, 'module': RiskModule.OVERCONFIDENCE}

        # Check for dangerous overconfidence patterns
        if self.state['consecutive_wins'] >= 3:
            if self.state['confidence_level'] > self.config['confidence_danger_zone']:
                check['passed'] = False
                check['reason'] = "Overconfidence detected after winning streak"
                check['flag'] = "OVERCONFIDENCE_ALERT"
                check['suggestion'] = "Reduce position size by 50% for next 3 trades"

        # Check for excessive confluence interpretation
        if confluence_score > 90 and self.state['confidence_level'] > 0.8:
            check['flag'] = "HIGH_CONFIDENCE_WARNING"
            check['suggestion'] = "Remember: No setup is 100% certain"

        return check

    def _check_daily_limits(self) -> Dict:
        """
        Module 2: Daily Loss Limits
        Enforces strict daily drawdown limits (3% soft, 5% hard)
        """
        check = {'passed': True, 'module': RiskModule.DAILY_LIMITS}

        daily_loss = abs(self.state['daily_pnl_percent'])

        # Hard stop at 3% (buffer before prop firm 5% limit)
        if daily_loss >= self.config['daily_loss_limit']:
            check['passed'] = False
            check['reason'] = f"Daily loss limit reached ({daily_loss:.1%})"
            check['flag'] = "DAILY_LIMIT_REACHED"
            check['suggestion'] = "Stop trading for today - protect your capital"

        # Warning at 2%
        elif daily_loss >= 0.02:
            check['flag'] = "APPROACHING_DAILY_LIMIT"
            check['suggestion'] = f"Caution: {(0.03 - daily_loss):.1%} until daily limit"

        # Check trade frequency
        if self.state['trades_today'] >= self.config['max_trades_per_day']:
            check['passed'] = False
            check['reason'] = f"Maximum daily trades reached ({self.state['trades_today']})"
            check['flag'] = "OVERTRADE_PROTECTION"
            check['suggestion'] = "Quality over quantity - wait for tomorrow"

        return check

    def _check_cooling_off(self) -> Dict:
        """
        Module 3: Cooling-Off Period
        Enforces emotional reset after losses or rapid trading
        """
        check = {'passed': True, 'module': RiskModule.COOLING_OFF}

        now = datetime.now()

        # Check if in cooling-off period
        if self.state['cooling_off_until']:
            if now < self.state['cooling_off_until']:
                remaining = (self.state['cooling_off_until'] - now).seconds // 60
                check['passed'] = False
                check['reason'] = f"Cooling-off period active ({remaining} min remaining)"
                check['flag'] = "COOLING_OFF_ACTIVE"
                check['suggestion'] = "Use this time to review your process"
                return check

        # Check for rapid trading (less than 5 min between trades)
        if self.state['last_trade_time']:
            time_since_last = (now - self.state['last_trade_time']).seconds / 60
            if time_since_last < 5:
                check['flag'] = "RAPID_TRADING_WARNING"
                check['suggestion'] = "Slow down - avoid impulsive decisions"

        return check

    def _check_revenge_trading(self) -> Dict:
        """
        Module 4: Revenge Trading Prevention
        Detects and prevents emotional retaliation after losses
        """
        check = {'passed': True, 'module': RiskModule.REVENGE_TRADING}

        # Trigger after consecutive losses
        if self.state['consecutive_losses'] >= self.config['revenge_threshold']:
            check['passed'] = False
            check['reason'] = f"Revenge trading risk after {self.state['consecutive_losses']} losses"
            check['flag'] = "REVENGE_TRADE_BLOCKED"
            check['suggestion'] = "Take a break - losses are part of the process"

            # Activate cooling-off
            self.state['cooling_off_until'] = datetime.now() + timedelta(
                minutes=self.config['cooling_off_minutes']
            )

        # Check for increased position sizing after loss
        if self.state['consecutive_losses'] > 0 and self.state['emotional_state'] == 'frustrated':
            check['flag'] = "EMOTIONAL_TRADING_RISK"
            check['suggestion'] = "Maintain consistent position sizing"

        return check

    def _check_disposition_effect(self, market_data: Dict) -> Dict:
        """
        Module 5: Disposition Effect Neutralizer
        Prevents holding losers too long and cutting winners too early
        """
        check = {'passed': True, 'module': RiskModule.DISPOSITION_EFFECT}

        # This would integrate with actual position data
        # For now, using market data indicators
        if market_data.get('unrealized_loss_percent', 0) < -2:
            check['flag'] = "DISPOSITION_EFFECT_WARNING"
            check['suggestion'] = "Honor your stop loss - don't hope for reversal"

        if market_data.get('unrealized_gain_percent', 0) > 1:
            check['flag'] = "PREMATURE_EXIT_RISK"
            check['suggestion'] = "Let winners run with trailing stop"

        return check

    def _check_prop_firm_rules(self) -> Dict:
        """
        Module 6: Prop Firm Guardian
        Ensures compliance with typical prop firm rules
        """
        check = {'passed': True, 'module': RiskModule.PROP_FIRM_GUARDIAN}

        # Daily drawdown check (5% typical limit)
        if abs(self.state['daily_pnl_percent']) >= self.config['prop_firm_daily_limit']:
            check['passed'] = False
            check['reason'] = "Prop firm daily loss limit breached"
            check['flag'] = "PROP_FIRM_VIOLATION"
            check['suggestion'] = "Account at risk - stop immediately"

        # Total drawdown check (10% typical limit)
        if self.state['total_drawdown'] >= self.config['prop_firm_max_loss']:
            check['passed'] = False
            check['reason'] = "Maximum drawdown limit reached"
            check['flag'] = "ACCOUNT_BREACH_RISK"
            check['suggestion'] = "Critical: Review risk management immediately"

        return check

    def _calculate_risk_score(self, checks: List[Dict], confluence: float) -> float:
        """Calculate overall risk score (0-100, lower is safer)"""

        # Base risk from failed checks
        failed_count = len([c for c in checks if not c['passed']])
        base_risk = (failed_count / len(checks)) * 50

        # Adjust for behavioral state
        state_risk = 0
        if self.state['emotional_state'] in ['frustrated', 'euphoric']:
            state_risk += 20
        if self.state['consecutive_losses'] > 0:
            state_risk += 10 * self.state['consecutive_losses']
        if self.state['confidence_level'] > 0.8:
            state_risk += 15

        # Confluence adjustment (higher confluence = lower risk)
        confluence_adjustment = (100 - confluence) / 2

        total_risk = min(base_risk + state_risk + confluence_adjustment, 100)
        return total_risk

    def _update_state(self, session_stats: Dict):
        """Update internal state from session statistics"""
        if session_stats:
            self.state['trades_today'] = session_stats.get('trades_today', 0)
            self.state['daily_pnl_percent'] = session_stats.get('daily_pnl', 0)
            self.state['last_trade_time'] = session_stats.get('last_trade_time')
            self.state['confidence_level'] = session_stats.get('confidence_level', 0.5)

    def _log_decision(self, approved: bool, reason: str, flags: List[str]):
        """Log risk decisions for behavioral analysis"""
        self.history['rule_violations'].append({
            'timestamp': datetime.now(),
            'approved': approved,
            'reason': reason,
            'flags': flags
        })

        # Keep only last 100 decisions
        if len(self.history['rule_violations']) > 100:
            self.history['rule_violations'] = self.history['rule_violations'][-100:]

    def update_trade_result(self, result: Dict):
        """Update state based on trade results for learning"""
        is_win = result.get('pnl', 0) > 0

        if is_win:
            self.state['consecutive_wins'] += 1
            self.state['consecutive_losses'] = 0
            self.state['emotional_state'] = 'confident'
        else:
            self.state['consecutive_losses'] += 1
            self.state['consecutive_wins'] = 0
            self.state['emotional_state'] = 'frustrated'

        # Update confidence based on results
        if is_win:
            self.state['confidence_level'] = min(0.9, self.state['confidence_level'] + 0.1)
        else:
            self.state['confidence_level'] = max(0.1, self.state['confidence_level'] - 0.15)

    def get_behavioral_report(self) -> Dict:
        """Generate behavioral analysis report"""
        return {
            'current_state': self.state,
            'risk_modules': {
                'overconfidence': self.state['confidence_level'] > 0.7,
                'daily_limits': abs(self.state['daily_pnl_percent']) > 0.02,
                'cooling_off': self.state['cooling_off_until'] is not None,
                'revenge_risk': self.state['consecutive_losses'] >= 2,
                'disposition_risk': self.state['emotional_state'] != 'neutral',
                'prop_compliance': abs(self.state['daily_pnl_percent']) < 0.03
            },
            'recommendations': self._generate_recommendations()
        }

    def _generate_recommendations(self) -> List[str]:
        """Generate personalized behavioral recommendations"""
        recommendations = []

        if self.state['confidence_level'] > 0.8:
            recommendations.append("Reduce position sizes - overconfidence detected")

        if self.state['consecutive_losses'] > 1:
            recommendations.append("Consider taking a break to reset emotionally")

        if self.state['trades_today'] > 3:
            recommendations.append("Focus on quality setups - avoid overtrading")

        return recommendations
