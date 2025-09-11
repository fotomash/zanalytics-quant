from core.predictive_scorer import PredictiveScorer

def run(state, config):
    scorer = PredictiveScorer(config)
    result = scorer.score(state)
    state.update(result)
    return state
