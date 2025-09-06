"""
ConfluenceScorer - Multi-Strategy Signal Fusion
Wraps existing analyzers to produce unified scoring
"""

import numpy as np
from typing import Dict, List, Tuple
import logging

# Import existing analyzers (these already exist in the codebase)
from components.smc_analyser import SMCAnalyzer
from components.wyckoff_analyzer import WyckoffAnalyzer  
from components.technical_analysis import TechnicalAnalysis

logger = logging.getLogger(__name__)

class ConfluenceScorer:
    """
    Combines signals from multiple analysis methods into a single score.
    This is a lightweight wrapper around existing heavy analyzers.
    """

    def __init__(self, config: Dict = None):
        # Initialize existing analyzers
        self.smc = SMCAnalyzer()           # 35,895 LOC
        self.wyckoff = WyckoffAnalyzer()   # 15,011 LOC
        self.technical = TechnicalAnalysis() # 8,161 LOC

        # Default weights (configurable)
        self.weights = config.get('weights', {
            'smc': 0.4,
            'wyckoff': 0.3,
            'technical': 0.3
        }) if config else {
            'smc': 0.4,
            'wyckoff': 0.3,
            'technical': 0.3
        }

        # Score thresholds
        self.thresholds = {
            'high': 80,
            'medium': 60,
            'low': 40
        }

    def score(self, data: Dict) -> Dict:
        """
        Calculate confluence score from market data.

        Args:
            data: Normalized market data frame

        Returns:
            Dict with score, grade, components, and reasons
        """
        try:
            # Get individual scores
            smc_result = self._score_smc(data)
            wyckoff_result = self._score_wyckoff(data)
            technical_result = self._score_technical(data)

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
                'score': round(final_score, 1),
                'grade': grade,
                'components': {
                    'smc': smc_result['score'],
                    'wyckoff': wyckoff_result['score'],
                    'technical': technical_result['score']
                },
                'reasons': reasons,
                'details': {
                    'smc': smc_result['details'],
                    'wyckoff': wyckoff_result['details'],
                    'technical': technical_result['details']
                }
            }

        except Exception as e:
            logger.error(f"Error calculating confluence score: {e}")
            return {
                'score': 0,
                'grade': 'error',
                'components': {},
                'reasons': [f'Error: {str(e)}']
            }

    def _score_smc(self, data: Dict) -> Dict:
        """Calculate SMC-based score"""
        # Call existing SMC analyzer
        smc_analysis = self.smc.analyze(data.get('df', {}))

        score = 0
        details = []

        # Score based on SMC concepts
        if smc_analysis.get('order_blocks'):
            score += 30
            details.append('Order block detected')

        if smc_analysis.get('fair_value_gaps'):
            score += 25
            details.append('Fair value gap present')

        if smc_analysis.get('liquidity_sweeps'):
            score += 25
            details.append('Liquidity sweep confirmed')

        if smc_analysis.get('displacement'):
            score += 20
            details.append('Strong displacement')

        return {
            'score': min(100, score),
            'details': details
        }

    def _score_wyckoff(self, data: Dict) -> Dict:
        """Calculate Wyckoff-based score"""
        # Call existing Wyckoff analyzer
        wyckoff_analysis = self.wyckoff.analyze(data.get('df', {}))

        score = 0
        details = []

        # Score based on Wyckoff phases
        phase = wyckoff_analysis.get('current_phase', '')

        if phase == 'Accumulation':
            score += 40
            details.append('Accumulation phase')

        if 'spring' in str(wyckoff_analysis.get('spring_upthrust', {})):
            score += 35
            details.append('Wyckoff spring detected')

        if wyckoff_analysis.get('sos_sow'):
            score += 25
            details.append('Sign of strength')

        return {
            'score': min(100, score),
            'details': details
        }

    def _score_technical(self, data: Dict) -> Dict:
        """Calculate technical indicator score"""
        # Call existing technical analysis
        ta_analysis = self.technical.calculate_all(data.get('df', {}))

        score = 0
        details = []

        # RSI conditions
        rsi = ta_analysis.get('rsi', {})
        if isinstance(rsi, dict):
            rsi_value = rsi.get('value', 50)
        else:
            rsi_value = 50

        if rsi_value < 30:
            score += 25
            details.append('RSI oversold')
        elif rsi_value > 70:
            score += 25
            details.append('RSI overbought')

        # MACD conditions
        macd_diff = ta_analysis.get('macd_diff', 0)
        if macd_diff > 0:
            score += 25
            details.append('MACD bullish')

        # Support/Resistance
        if ta_analysis.get('support_resistance'):
            score += 25
            details.append('Near key level')

        # Volume confirmation
        if self._check_volume_confirmation(ta_analysis):
            score += 25
            details.append('Volume confirms')

        return {
            'score': min(100, score),
            'details': details
        }

    def _check_volume_confirmation(self, ta_analysis: Dict) -> bool:
        """Check if volume confirms the move"""
        # Simplified volume check
        return ta_analysis.get('volume_sma', 0) > 0

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
