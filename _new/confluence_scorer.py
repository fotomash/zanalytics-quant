"""
ConfluenceScorer - Multi-Strategy Confluence Wrapper
Integrates existing SMC, Wyckoff, and Technical Analysis components
"""

import numpy as np
from typing import Dict, Any, List, Tuple
import logging
import yaml

class ConfluenceScorer:
    """
    Wraps existing analyzers (SMC, Wyckoff, Technical) into unified 0-100 score.
    Implements probability-based scoring aligned with Trading in the Zone principles.
    """

    def __init__(self, config_path: str = "pulse_config.yaml"):
        """Initialize with configurable weights for each analyzer"""
        self.logger = logging.getLogger(__name__)

        # Default configuration (can be overridden by config file)
        self.config = {
            'weights': {
                'smc': 0.4,        # Smart Money Concepts weight
                'wyckoff': 0.3,    # Wyckoff analysis weight
                'technical': 0.3   # Technical indicators weight
            },
            'thresholds': {
                'strong_signal': 80,
                'moderate_signal': 60,
                'weak_signal': 40
            },
            'confluence_multipliers': {
                'all_aligned': 1.2,      # Boost when all agree
                'majority_aligned': 1.1,  # Boost when 2/3 agree
                'divergence_penalty': 0.8 # Reduce on disagreement
            }
        }

        # Load custom configuration if exists
        try:
            with open(config_path, 'r') as f:
                custom_config = yaml.safe_load(f)
                if custom_config:
                    self.config.update(custom_config)
        except FileNotFoundError:
            self.logger.info(f"Using default configuration (no {config_path} found)")

        # Component scores cache for analysis
        self.last_component_scores = {}

        self.logger.info("ConfluenceScorer initialized with weights: %s", 
                        self.config['weights'])

    def score(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate confluence score from multiple analysis methods.

        Returns:
            Dict with 'score' (0-100) and 'components' breakdown
        """
        try:
            # Get individual component scores
            smc_score = self._calculate_smc_score(data)
            wyckoff_score = self._calculate_wyckoff_score(data)
            technical_score = self._calculate_technical_score(data)

            # Store component scores
            self.last_component_scores = {
                'smc': smc_score,
                'wyckoff': wyckoff_score,
                'technical': technical_score
            }

            # Calculate weighted base score
            weights = self.config['weights']
            base_score = (
                smc_score * weights['smc'] +
                wyckoff_score * weights['wyckoff'] +
                technical_score * weights['technical']
            )

            # Apply confluence multipliers
            final_score = self._apply_confluence_logic(
                base_score, 
                smc_score, 
                wyckoff_score, 
                technical_score
            )

            # Build detailed response
            return {
                'score': round(final_score, 2),
                'components': {
                    'smc': round(smc_score, 2),
                    'wyckoff': round(wyckoff_score, 2),
                    'technical': round(technical_score, 2)
                },
                'signal_strength': self._classify_signal_strength(final_score),
                'alignment': self._calculate_alignment(
                    smc_score, wyckoff_score, technical_score
                ),
                'reasoning': self._generate_reasoning(final_score)
            }

        except Exception as e:
            self.logger.error(f"ConfluenceScorer error: {e}")
            return {
                'score': 0,
                'components': {},
                'error': str(e)
            }

    def _calculate_smc_score(self, data: Dict) -> float:
        """
        Calculate Smart Money Concepts score.
        Wraps existing SMC analyzer or uses simplified logic.
        """
        score = 0.0

        # Order blocks detection
        if self._detect_order_block(data):
            score += 25

        # Fair Value Gap (FVG) detection
        if self._detect_fvg(data):
            score += 20

        # Liquidity sweep detection
        if self._detect_liquidity_sweep(data):
            score += 25

        # Market structure shift
        if self._detect_structure_shift(data):
            score += 30

        return min(score, 100)

    def _calculate_wyckoff_score(self, data: Dict) -> float:
        """
        Calculate Wyckoff analysis score.
        Wraps existing Wyckoff analyzer or uses simplified logic.
        """
        score = 0.0

        # Volume analysis
        volume_score = self._analyze_volume_pattern(data)
        score += volume_score * 0.3

        # Price action phases
        phase_score = self._identify_wyckoff_phase(data)
        score += phase_score * 0.4

        # Spring/Test detection
        if self._detect_spring_test(data):
            score += 30

        return min(score, 100)

    def _calculate_technical_score(self, data: Dict) -> float:
        """
        Calculate technical indicators score.
        Wraps existing technical analysis or uses simplified logic.
        """
        score = 0.0
        indicators_aligned = 0
        total_indicators = 0

        # RSI analysis
        if 'rsi' in data:
            total_indicators += 1
            if 30 < data['rsi'] < 70:  # Not overbought/oversold
                if (data['rsi'] > 50 and data.get('trend') == 'up') or                    (data['rsi'] < 50 and data.get('trend') == 'down'):
                    indicators_aligned += 1

        # MACD analysis
        if 'macd' in data and 'macd_signal' in data:
            total_indicators += 1
            if data['macd'] > data['macd_signal']:
                indicators_aligned += 1

        # Moving averages
        if 'ema_20' in data and 'ema_50' in data:
            total_indicators += 1
            if data['close'] > data['ema_20'] > data['ema_50']:
                indicators_aligned += 1

        # Calculate percentage alignment
        if total_indicators > 0:
            score = (indicators_aligned / total_indicators) * 100

        return score

    def _apply_confluence_logic(
        self, 
        base_score: float,
        smc: float, 
        wyckoff: float, 
        technical: float
    ) -> float:
        """Apply confluence multipliers based on agreement between methods"""

        # Count how many methods show strong signals
        strong_signals = sum([
            1 for score in [smc, wyckoff, technical] 
            if score >= self.config['thresholds']['strong_signal']
        ])

        # Apply multipliers
        multipliers = self.config['confluence_multipliers']

        if strong_signals == 3:
            # All methods strongly agree
            return min(base_score * multipliers['all_aligned'], 100)
        elif strong_signals >= 2:
            # Majority agreement
            return min(base_score * multipliers['majority_aligned'], 100)
        elif max(smc, wyckoff, technical) - min(smc, wyckoff, technical) > 40:
            # High divergence between methods
            return base_score * multipliers['divergence_penalty']

        return base_score

    def _classify_signal_strength(self, score: float) -> str:
        """Classify signal strength based on score"""
        thresholds = self.config['thresholds']

        if score >= thresholds['strong_signal']:
            return 'STRONG'
        elif score >= thresholds['moderate_signal']:
            return 'MODERATE'
        elif score >= thresholds['weak_signal']:
            return 'WEAK'
        else:
            return 'NO_SIGNAL'

    def _calculate_alignment(self, smc: float, wyckoff: float, technical: float) -> str:
        """Calculate alignment between different analysis methods"""
        scores = [smc, wyckoff, technical]
        std_dev = np.std(scores)

        if std_dev < 10:
            return 'HIGH_ALIGNMENT'
        elif std_dev < 20:
            return 'MODERATE_ALIGNMENT'
        else:
            return 'LOW_ALIGNMENT'

    def _generate_reasoning(self, score: float) -> str:
        """Generate human-readable reasoning for the score"""
        components = self.last_component_scores
        reasons = []

        # Identify strongest component
        if components:
            strongest = max(components.items(), key=lambda x: x[1])
            reasons.append(f"{strongest[0].upper()} leading at {strongest[1]:.1f}")

        # Add signal strength
        strength = self._classify_signal_strength(score)
        reasons.append(f"{strength} signal confidence")

        # Add probability context (Trading in the Zone principle)
        if score >= 60:
            reasons.append(f"Probability favors entry ({score:.0f}% confluence)")
        else:
            reasons.append("Await higher confluence")

        return " | ".join(reasons)

    # Simplified detection methods (replace with actual analyzer calls)
    def _detect_order_block(self, data: Dict) -> bool:
        """Simplified order block detection"""
        return data.get('order_block_detected', False)

    def _detect_fvg(self, data: Dict) -> bool:
        """Simplified Fair Value Gap detection"""
        return data.get('fvg_detected', False)

    def _detect_liquidity_sweep(self, data: Dict) -> bool:
        """Simplified liquidity sweep detection"""
        return data.get('liquidity_sweep', False)

    def _detect_structure_shift(self, data: Dict) -> bool:
        """Simplified market structure shift detection"""
        return data.get('structure_shift', False)

    def _analyze_volume_pattern(self, data: Dict) -> float:
        """Simplified volume pattern analysis"""
        return data.get('volume_score', 50.0)

    def _identify_wyckoff_phase(self, data: Dict) -> float:
        """Simplified Wyckoff phase identification"""
        return data.get('wyckoff_phase_score', 50.0)

    def _detect_spring_test(self, data: Dict) -> bool:
        """Simplified spring/test detection"""
        return data.get('spring_detected', False)
