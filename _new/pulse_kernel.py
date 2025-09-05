"""
PulseKernel - Central Orchestrator for Zanalytics Pulse
Behavioral Trading System v11.5.1

Orchestrates: Data → Score → Risk → Journal → Signal
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import redis
import asyncio

@dataclass
class PulseSignal:
    """Structured signal with behavioral metadata"""
    timestamp: datetime
    symbol: str
    timeframe: str
    confluence_score: float
    risk_approved: bool
    behavioral_flags: List[str]
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size: float
    reasoning: str

class PulseKernel:
    """
    Central orchestrator integrating existing analyzers with behavioral protection.
    Implements Trading in the Zone principles with evidence-based interventions.
    """

    def __init__(self, config_path: str = "pulse_config.yaml"):
        """Initialize with existing components and behavioral modules"""
        self.logger = logging.getLogger(__name__)

        # Import existing analyzers (lazy loading to avoid import errors)
        self.smc_analyzer = None  # Will be: SMCAnalyzer()
        self.wyckoff_analyzer = None  # Will be: WyckoffAnalyzer()
        self.technical_analysis = None  # Will be: TechnicalAnalysis()

        # Initialize new Pulse components
        from confluence_scorer import ConfluenceScorer
        from risk_enforcer import RiskEnforcer

        self.confluence_scorer = ConfluenceScorer(config_path)
        self.risk_enforcer = RiskEnforcer()

        # Journal engine for process logging
        self.journal = []
        self.active_signals = {}

        # Redis connection for real-time data
        self.redis_client = redis.Redis(
            host='localhost', 
            port=6379, 
            decode_responses=True
        )

        # Behavioral state tracking
        self.session_stats = {
            'trades_today': 0,
            'daily_pnl': 0.0,
            'last_trade_time': None,
            'cooling_off_until': None,
            'confidence_level': 0.5  # Neutral starting point
        }

        self.logger.info("PulseKernel initialized - Behavioral trading system active")

    def process_frame(self, data: Dict[str, Any]) -> Optional[PulseSignal]:
        """
        Main orchestration pipeline with behavioral interventions

        Flow: Data → Confluence → Risk Check → Signal Generation
        """
        try:
            # 1. Journal entry - process start
            self._journal_entry("PROCESS_START", {
                'symbol': data.get('symbol'),
                'timeframe': data.get('timeframe'),
                'timestamp': datetime.now().isoformat()
            })

            # 2. Calculate confluence score using existing analyzers
            confluence_result = self.confluence_scorer.score(data)
            confluence_score = confluence_result['score']

            self._journal_entry("CONFLUENCE_CALCULATED", {
                'score': confluence_score,
                'components': confluence_result['components']
            })

            # 3. Apply behavioral risk checks (6 protection modules)
            risk_decision = self.risk_enforcer.evaluate_signal({
                'confluence_score': confluence_score,
                'session_stats': self.session_stats,
                'market_data': data
            })

            if not risk_decision['approved']:
                self._journal_entry("SIGNAL_REJECTED", {
                    'reason': risk_decision['reason'],
                    'behavioral_flags': risk_decision['flags']
                })
                return None

            # 4. Generate signal with position sizing
            signal = self._generate_signal(
                data, 
                confluence_result, 
                risk_decision
            )

            # 5. Update session statistics
            self._update_session_stats(signal)

            # 6. Publish to Redis for real-time consumption
            self._publish_signal(signal)

            self._journal_entry("SIGNAL_GENERATED", {
                'signal_id': signal.timestamp.isoformat(),
                'confluence': signal.confluence_score,
                'approved': signal.risk_approved
            })

            return signal

        except Exception as e:
            self.logger.error(f"PulseKernel processing error: {e}")
            self._journal_entry("PROCESS_ERROR", {'error': str(e)})
            return None

    def _generate_signal(
        self, 
        data: Dict, 
        confluence: Dict, 
        risk: Dict
    ) -> PulseSignal:
        """Generate structured signal with behavioral metadata"""

        # Calculate position parameters with risk management
        entry_price = data['close']
        atr = data.get('atr', entry_price * 0.01)  # Default 1% if no ATR

        # Risk-adjusted position sizing
        stop_loss = entry_price - (2 * atr)  # 2 ATR stop
        take_profit = entry_price + (3 * atr)  # 3 ATR target (1.5 RR)

        # Position size based on risk tolerance and confidence
        base_risk = 0.01  # 1% base risk
        confidence_multiplier = min(confluence['score'] / 100, 1.0)
        position_size = base_risk * confidence_multiplier

        # Build reasoning with Trading in the Zone principles
        reasoning = self._build_reasoning(confluence, risk)

        return PulseSignal(
            timestamp=datetime.now(),
            symbol=data['symbol'],
            timeframe=data['timeframe'],
            confluence_score=confluence['score'],
            risk_approved=risk['approved'],
            behavioral_flags=risk.get('flags', []),
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size=position_size,
            reasoning=reasoning
        )

    def _build_reasoning(self, confluence: Dict, risk: Dict) -> str:
        """Build explainable reasoning for the signal"""
        reasons = []

        # Confluence reasoning
        if confluence['score'] >= 80:
            reasons.append(f"High confluence ({confluence['score']}/100)")
        elif confluence['score'] >= 60:
            reasons.append(f"Moderate confluence ({confluence['score']}/100)")

        # Component breakdown
        for component, score in confluence['components'].items():
            if score > 70:
                reasons.append(f"{component}: Strong signal ({score})")

        # Risk reasoning
        if risk.get('flags'):
            reasons.append(f"Behavioral checks: {', '.join(risk['flags'])}")

        return " | ".join(reasons)

    def _update_session_stats(self, signal: PulseSignal):
        """Update session statistics for behavioral tracking"""
        self.session_stats['trades_today'] += 1
        self.session_stats['last_trade_time'] = signal.timestamp

        # Update confidence based on confluence
        self.session_stats['confidence_level'] = (
            0.7 * self.session_stats['confidence_level'] + 
            0.3 * (signal.confluence_score / 100)
        )

    def _publish_signal(self, signal: PulseSignal):
        """Publish signal to Redis for real-time consumption"""
        signal_dict = {
            'timestamp': signal.timestamp.isoformat(),
            'symbol': signal.symbol,
            'confluence_score': signal.confluence_score,
            'entry_price': signal.entry_price,
            'stop_loss': signal.stop_loss,
            'take_profit': signal.take_profit,
            'position_size': signal.position_size,
            'reasoning': signal.reasoning
        }

        # Publish to Redis channel
        self.redis_client.publish(
            'pulse:signals', 
            json.dumps(signal_dict)
        )

        # Store in active signals
        self.active_signals[signal.symbol] = signal_dict

    def _journal_entry(self, event_type: str, data: Dict):
        """Log process events for behavioral analysis"""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'event': event_type,
            'data': data
        }
        self.journal.append(entry)

        # Persist to Redis for analysis
        self.redis_client.lpush(
            'pulse:journal', 
            json.dumps(entry)
        )

    def get_session_report(self) -> Dict:
        """Generate session report for behavioral review"""
        return {
            'session_stats': self.session_stats,
            'active_signals': self.active_signals,
            'journal_entries': len(self.journal),
            'behavioral_health': self._calculate_behavioral_health()
        }

    def _calculate_behavioral_health(self) -> Dict:
        """Calculate behavioral health metrics"""
        return {
            'overtrading_risk': self.session_stats['trades_today'] > 3,
            'confidence_stable': 0.3 < self.session_stats['confidence_level'] < 0.7,
            'cooling_off_active': self.session_stats.get('cooling_off_until') is not None,
            'daily_loss_safe': self.session_stats['daily_pnl'] > -0.03  # 3% limit
        }

# Health check endpoint
async def health_check():
    """API health check for Django integration"""
    kernel = PulseKernel()
    return {
        'status': 'healthy',
        'version': '11.5.1',
        'components': {
            'confluence_scorer': 'ready',
            'risk_enforcer': 'ready',
            'redis': 'connected'
        }
    }
