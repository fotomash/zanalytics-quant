"""Multi-Timeframe Conflict Resolution"""

from typing import Dict


class MultiTFResolver:
    """Resolve conflicts between different timeframe signals"""

    def __init__(self):
        self.tf_weights = {
            'M1': 0.1,   # Noise filter
            'M5': 0.2,   # Entry timing
            'M15': 0.3,  # Trend confirmation
            'H1': 0.25,  # Structure
            'H4': 0.15   # Major trend
        }

    def resolve_conflicts(self, tf_scores: Dict[str, float]) -> Dict:
        """Resolve multi-timeframe conflicts"""

        # Calculate weighted score
        weighted_score = sum(
            score * self.tf_weights.get(tf, 0.1)
            for tf, score in tf_scores.items()
        )

        # Check for major conflicts
        scores = list(tf_scores.values())
        if scores and max(scores) - min(scores) > 40:  # High divergence
            return {
                'score': weighted_score * 0.9,  # Apply penalty
                'conflict': True,
                'reason': 'Timeframe divergence detected'
            }

        return {
            'score': weighted_score,
            'conflict': False,
            'alignment': 'Good MTF alignment'
        }
