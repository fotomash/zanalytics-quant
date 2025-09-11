"""Predictive scoring utilities.

This module was formerly :mod:`confluence_scorer` and has been relocated to
``core.predictive_scorer``.  The :class:`PredictiveScorer` combines multiple
analysis engines to produce a single maturity score and grade.  For backward
compatibility the same implementation is also exposed as
``ConfluenceStacker``.
"""

import numpy as np
from typing import Dict, List, Tuple
import logging
import yaml
import pandas as pd

# Import existing analyzers (these already exist in the codebase)
from .smc_analyzer import SMCAnalyzer
from .wyckoff_analyzer import WyckoffAnalyzer
from components.technical_analysis import TechnicalAnalysis

logger = logging.getLogger(__name__)


class PredictiveScorer:
    """Combine signals from multiple analysis methods into a single score."""

    def __init__(self, config: Dict | str | None = None):
        """Initialize the scorer.

        Parameters
        ----------
        config:
            Optional configuration dictionary or path to a YAML file. If a
            string is provided, the file will be loaded.  Missing files or
            invalid YAML result in an empty configuration.
        """

        if isinstance(config, str):
            try:
                with open(config, "r") as f:
                    config = yaml.safe_load(f) or {}
            except Exception:
                config = {}
        else:
            config = config or {}

        # Initialize existing analyzers
        self.smc = SMCAnalyzer()
        self.wyckoff = WyckoffAnalyzer()
        self.technical = TechnicalAnalysis()

        # Default weights (configurable)
        self.weights = config.get('weights', {
            'smc': 0.4,
            'wyckoff': 0.3,
            'technical': 0.3
        })

        # Score thresholds
        self.thresholds = {
            'high': 80,
            'medium': 60,
            'low': 40
        }
        
    def score(self, state: Dict) -> Dict:
        """Calculate maturity score using pre-populated ``state`` data.

        The enrichment pipeline fills ``state`` with intermediate analysis
        results (e.g. liquidity zones, Wyckoff phase, technical indicators).
        This method consumes those values directly and only falls back to
        running the heavier analyzers when specific keys are missing.

        Parameters
        ----------
        state:
            Dictionary containing analysis data and optionally the price
            DataFrame under ``df`` or ``dataframe``.

        Returns
        -------
        Dict
            ``maturity_score`` and ``grade`` along with diagnostic details.
        """
        try:
            # Each scoring component pulls the necessary information from the
            # provided ``state`` and performs its own fallback calculation if
            # required.
            smc_result = self._score_smc(state)
            wyckoff_result = self._score_wyckoff(state)
            technical_result = self._score_technical(state)
            
            # Calculate weighted score
            final_score = (
                smc_result['score'] * self.weights['smc'] +
                wyckoff_result['score'] * self.weights['wyckoff'] +
                technical_result['score'] * self.weights['technical']
            )
            
            # Determine grade
            grade = self._calculate_grade(final_score)
            
            # Compile reasons
            reasons = self._compile_reasons(
                smc_result, 
                wyckoff_result, 
                technical_result,
                final_score
            )
            
            return {
                'maturity_score': round(final_score, 1),
                'grade': grade,
                'components': {
                    'smc': smc_result['score'],
                    'wyckoff': wyckoff_result['score'],
                    'technical': technical_result['score'],
                },
                'reasons': reasons,
                'reasoning': reasons,
                'details': {
                    'smc': smc_result['details'],
                    'wyckoff': wyckoff_result['details'],
                    'technical': technical_result['details'],
                },
            }
            
        except Exception as e:
            logger.error(f"Error calculating confluence score: {e}")
            return {
                'maturity_score': 0,
                'grade': 'error',
                'components': {},
                'reasons': [f'Error: {str(e)}'],
                'reasoning': [f'Error: {str(e)}'],
            }
    
    def _score_smc(self, state: Dict) -> Dict:
        """Calculate SMC-based score.

        The enrichment modules may have already populated ``state`` with SMC
        analysis fields.  When they are missing we fall back to running the
        :class:`SMCAnalyzer` directly.
        """
        needed = ['order_blocks', 'fair_value_gaps', 'liquidity_sweeps',
                  'displacement', 'liquidity_zones']
        missing = [k for k in needed if k not in state]
        if missing:
            analysis = self.smc.analyze(self._get_df(state))
            for k in needed:
                if k in analysis and k not in state:
                    state[k] = analysis[k]

        score = 0
        details = []

        if state.get('order_blocks'):
            score += 30
            details.append('Order block detected')

        if state.get('fair_value_gaps'):
            score += 25
            details.append('Fair value gap present')

        if state.get('liquidity_sweeps'):
            score += 25
            details.append('Liquidity sweep confirmed')

        if state.get('displacement'):
            score += 20
            details.append('Strong displacement')

        return {
            'score': min(100, score),
            'details': details
        }
    
    def _score_wyckoff(self, state: Dict) -> Dict:
        """Calculate Wyckoff-based score using precomputed data."""
        needed = ['current_phase', 'spring_upthrust', 'sos_sow']
        missing = [k for k in needed if k not in state]
        if missing:
            analysis = self.wyckoff.analyze(self._get_df(state))
            for k in needed:
                if k in analysis and k not in state:
                    state[k] = analysis[k]

        score = 0
        details = []

        phase = state.get('current_phase', '')
        if phase == 'Accumulation':
            score += 40
            details.append('Accumulation phase')

        if 'spring' in str(state.get('spring_upthrust', {})):
            score += 35
            details.append('Wyckoff spring detected')

        if state.get('sos_sow'):
            score += 25
            details.append('Sign of strength')

        return {
            'score': min(100, score),
            'details': details
        }
    
    def _score_technical(self, state: Dict) -> Dict:
        """Calculate technical indicator score using cached data."""
        needed = ['rsi', 'macd_diff', 'support_resistance', 'volume_sma']
        missing = [k for k in needed if k not in state]
        if missing:
            analysis = self.technical.calculate_all(self._get_df(state))
            for k in needed:
                if k in analysis and k not in state:
                    state[k] = analysis[k]

        score = 0
        details = []

        rsi = state.get('rsi', {})
        if isinstance(rsi, dict):
            rsi_value = rsi.get('value', 50)
        elif hasattr(rsi, 'iloc'):
            try:
                rsi_value = float(rsi.iloc[-1])
            except Exception:  # pragma: no cover - defensive
                rsi_value = 50
        else:
            try:
                rsi_value = float(rsi)
            except Exception:
                rsi_value = 50

        if rsi_value < 30:
            score += 25
            details.append('RSI oversold')
        elif rsi_value > 70:
            score += 25
            details.append('RSI overbought')

        macd_diff = state.get('macd_diff', 0)
        if hasattr(macd_diff, 'iloc'):
            try:
                macd_diff = float(macd_diff.iloc[-1])
            except Exception:
                macd_diff = 0

        if macd_diff > 0:
            score += 25
            details.append('MACD bullish')

        if state.get('support_resistance'):
            score += 25
            details.append('Near key level')

        if self._check_volume_confirmation(state):
            score += 25
            details.append('Volume confirms')

        return {
            'score': min(100, score),
            'details': details
        }

    def _get_df(self, data: Dict) -> pd.DataFrame:
        """Ensure analyzers receive a :class:`pandas.DataFrame`."""
        df = data.get('df') or data.get('dataframe')
        if isinstance(df, pd.DataFrame):
            return df
        return pd.DataFrame([
            {
                'open': data.get('open', 0),
                'high': data.get('high', 0),
                'low': data.get('low', 0),
                'close': data.get('close', 0),
                'volume': data.get('volume', 0),
            }
        ])
    
    def _check_volume_confirmation(self, ta_analysis: Dict) -> bool:
        """Check if volume confirms the move."""
        volume = ta_analysis.get('volume_sma', 0)
        if hasattr(volume, 'iloc'):
            try:
                volume = float(volume.iloc[-1])
            except Exception:
                volume = 0
        return volume > 0
    
    def _calculate_grade(self, score: float) -> str:
        """Convert numeric score to grade"""
        if score >= self.thresholds['high']:
            return 'high'
        elif score >= self.thresholds['medium']:
            return 'medium'
        elif score >= self.thresholds['low']:
            return 'low'
        else:
            return 'minimal'
    
    def _compile_reasons(self, smc: Dict, wyckoff: Dict, technical: Dict, score: float) -> List[str]:
        """Compile human-readable reasons for the score"""
        reasons = []
        
        # Add top reasons from each component
        if smc['score'] > 70:
            reasons.extend(smc['details'][:2])
        if wyckoff['score'] > 70:
            reasons.extend(wyckoff['details'][:2])
        if technical['score'] > 70:
            reasons.extend(technical['details'][:2])
            
        # Add overall assessment
        if score >= 80:
            reasons.insert(0, '🎯 HIGH CONFLUENCE SETUP')
        elif score >= 60:
            reasons.insert(0, '⚡ MEDIUM CONFLUENCE')
        else:
            reasons.insert(0, '⚠️ LOW CONFLUENCE')
            
        return reasons[:5]  # Limit to top 5 reasons


# Backwards compatible alias
ConfluenceStacker = PredictiveScorer

