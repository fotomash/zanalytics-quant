import yaml
import json
from typing import Dict
import pandas as pd
from components.wyckoff_scorer import WyckoffScorer


class PulseKernel:
    def __init__(self, config_path: str = "pulse_config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        self.wyckoff_scorer = WyckoffScorer(
            **self.config.get('wyckoff', {}).get('scorer_weights', {})
        )
        # self.confluence_scorer = ConfluenceScorer(config_path)
        # self.risk_enforcer = RiskEnforcer(self.config['risk_limits'])

    def on_frame(self, frame: Dict):
        score_details = self.wyckoff_scorer.score(pd.DataFrame(frame['bars']))
        return {"ts": frame["ts"], "symbol": frame["symbol"], "score": score_details, "decision": "allowed"}
