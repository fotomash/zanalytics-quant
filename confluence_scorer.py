import yaml
from typing import Dict


class ConfluenceScorer:
    def __init__(self, config_path: str = "pulse_config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        # self.smc_analyzer = SMCAnalyzer()
        # self.wyckoff_analyzer = WyckoffAnalyzer()

    def score(self, data: Dict, wyckoff_scorer_override=None) -> Dict:
        if wyckoff_scorer_override and 'bars' in data:
            import pandas as pd
            df = pd.DataFrame(data['bars'])
            wyckoff_result = wyckoff_scorer_override.score(df)
            wyckoff_score = wyckoff_result['score']
        else:
            wyckoff_score = 50.0

        smc_score = 50.0
        tech_score = 50.0
        weights = self.config['weights']
        total_score = (
            smc_score * weights['smc']
            + wyckoff_score * weights['wyckoff']
            + tech_score * weights['technical']
        )
        return {"score": total_score, "grade": "Medium", "reasons": ["Analysis complete"]}
