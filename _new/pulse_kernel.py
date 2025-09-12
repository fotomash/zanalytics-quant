"""
PulseKernel - Central Orchestrator for Zanalytics Pulse
Coordinates between analyzers, risk management, and UI
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import redis
import logging

logger = logging.getLogger(__name__)

class PulseKernel:
    """
    Central orchestration engine for the Pulse trading system.
    Manages data flow, scoring, risk enforcement, and journaling.
    """

    def __init__(self, config_path: str = "pulse_config.yaml"):
        self.config = self._load_config(config_path)
        self.redis_client = redis.Redis(**self.config['redis'])

        # Initialize components (these wrap existing analyzers)
        self.confluence_scorer = None  # Will be initialized with ConfluenceScorer
        self.risk_enforcer = None      # Will be initialized with RiskEnforcer
        self.journal = None             # Will be initialized with JournalEngine

        # State management
        self.active_signals = {}
        self.daily_stats = self._init_daily_stats()
        self.behavioral_state = "normal"

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file"""
        # In production, use proper YAML loading
        return {
            'redis': {'host': 'localhost', 'port': 6379, 'db': 0},
            'risk_limits': {
                'daily_loss_limit': 500,
                'max_trades_per_day': 5,
                'max_position_size': 0.02,
                'cooling_period_minutes': 15
            },
            'behavioral': {
                'revenge_trade_threshold': 3,
                'overconfidence_threshold': 4,
                'fatigue_hour': 22
            }
        }

    def _init_daily_stats(self) -> Dict:
        """Initialize daily statistics"""
        return {
            'trades_count': 0,
            'pnl': 0.0,
            'wins': 0,
            'losses': 0,
            'behavioral_score': 100,
            'violations': [],
            'last_trade_time': None
        }

    async def on_frame(self, data: Dict) -> Dict:
        """
        Process incoming data frame through the full pipeline.
        This is the main entry point for all market data.

        Args:
            data: Normalized frame from MIDAS adapter

        Returns:
            Decision dict with score, action, and reasons
        """
        try:
            # Step 1: Calculate confluence score
            confluence_result = await self._calculate_confluence(data)

            # Step 2: Check risk constraints
            risk_check = await self._enforce_risk(confluence_result)

            # Step 3: Check behavioral state
            behavioral_check = self._check_behavioral_state()

            # Step 4: Make final decision
            decision = self._make_decision(
                confluence_result, 
                risk_check, 
                behavioral_check
            )

            # Step 5: Journal the decision
            await self._journal_decision(decision)

            # Step 6: Publish to UI and Telegram
            await self._publish_decision(decision)

            return decision

        except Exception as e:
            logger.error(f"Error processing frame: {e}")
            return {'error': str(e), 'action': 'skip'}

    async def _calculate_confluence(self, data: Dict) -> Dict:
        """Calculate confluence score using existing analyzers"""
        # This will call the ConfluenceScorer which wraps:
        # - SMC Analyzer (35,895 LOC)
        # - Wyckoff Analyzer (15,011 LOC)  
        # - Technical Analysis (8,161 LOC)

        return {
            'score': 82,  # 0-100
            'grade': 'high',
            'components': {
                'smc': 85,
                'wyckoff': 78,
                'technical': 83
            },
            'reasons': [
                'Bullish order block detected',
                'Wyckoff spring confirmed',
                'RSI oversold bounce'
            ]
        }

    async def _enforce_risk(self, confluence_result: Dict) -> Dict:
        """Check risk constraints and limits"""
        # This will call the RiskEnforcer

        return {
            'allowed': True,
            'warnings': [],
            'remaining_trades': 2,
            'remaining_risk': 260,
            'cooling_active': False
        }

    def _check_behavioral_state(self) -> Dict:
        """Analyze trader's behavioral state"""
        current_hour = datetime.now().hour

        # Check various behavioral factors
        factors = {
            'time_of_day': 'normal' if 8 <= current_hour <= 20 else 'fatigue',
            'recent_losses': self._check_recent_losses(),
            'trade_frequency': self._check_trade_frequency(),
            'position_sizing': self._check_position_sizing()
        }

        # Calculate overall state
        if any(f == 'danger' for f in factors.values()):
            self.behavioral_state = 'danger'
        elif any(f == 'warning' for f in factors.values()):
            self.behavioral_state = 'warning'
        else:
            self.behavioral_state = 'normal'

        return {
            'state': self.behavioral_state,
            'factors': factors,
            'score': self._calculate_behavioral_score(factors)
        }

    def _check_recent_losses(self) -> str:
        """Check for revenge trading patterns"""
        if self.daily_stats['losses'] >= 3:
            return 'danger'
        elif self.daily_stats['losses'] >= 2:
            return 'warning'
        return 'normal'

    def _check_trade_frequency(self) -> str:
        """Check for overtrading"""
        if self.daily_stats['trades_count'] >= 4:
            return 'warning'
        return 'normal'

    def _check_position_sizing(self) -> str:
        """Check for aggressive position sizing"""
        # Would check actual position sizes from recent trades
        return 'normal'

    def _calculate_behavioral_score(self, factors: Dict) -> int:
        """Calculate behavioral score 0-100"""
        base_score = 100

        for factor, state in factors.items():
            if state == 'danger':
                base_score -= 30
            elif state == 'warning':
                base_score -= 15

        return max(0, base_score)

    def _make_decision(self, confluence: Dict, risk: Dict, behavioral: Dict) -> Dict:
        """Make final trading decision"""
        decision = {
            'timestamp': datetime.now().isoformat(),
            'action': 'none',
            'confidence': 0,
            'reasons': [],
            'warnings': []
        }

        # Decision logic
        if not risk['allowed']:
            decision['action'] = 'blocked'
            decision['reasons'].append('Risk limits exceeded')

        elif behavioral['state'] == 'danger':
            decision['action'] = 'warning'
            decision['warnings'].append('High-risk behavioral state detected')

        elif confluence['score'] >= 80:
            decision['action'] = 'signal'
            decision['confidence'] = confluence['score']
            decision['reasons'] = confluence['reasons']

        elif confluence['score'] >= 60:
            decision['action'] = 'watch'
            decision['confidence'] = confluence['score']
            decision['reasons'].append('Medium confluence - monitor closely')

        return decision

    async def _journal_decision(self, decision: Dict):
        """Log decision to journal for later analysis"""
        journal_entry = {
            **decision,
            'behavioral_state': self.behavioral_state,
            'daily_stats': self.daily_stats.copy()
        }

        # Store in Redis
        key = f"journal:{datetime.now().strftime('%Y%m%d')}:{decision['timestamp']}"
        self.redis_client.set(key, json.dumps(journal_entry))

    async def _publish_decision(self, decision: Dict):
        """Publish decision to UI and notification channels"""
        # Publish to Redis for Streamlit
        self.redis_client.publish('pulse:decisions', json.dumps(decision))

        # Send to Discord if significant
        if decision['action'] in ['signal', 'blocked', 'warning']:
            await self._send_discord_alert(decision)

    async def _send_discord_alert(self, decision: Dict):
        """Send alert to Discord bot"""
        # Discord integration would go here
        pass

    def get_status(self) -> Dict:
        """Get current system status"""
        return {
            'behavioral_state': self.behavioral_state,
            'daily_stats': self.daily_stats,
            'active_signals': len(self.active_signals),
            'system_health': 'operational'
        }

# API Endpoints for Django Integration
async def process_frame(request_data: Dict) -> Dict:
    """Django endpoint: /api/pulse/frame"""
    kernel = PulseKernel()
    return await kernel.on_frame(request_data)

def get_health() -> Dict:
    """Django endpoint: /api/pulse/health"""
    kernel = PulseKernel()
    return kernel.get_status()
