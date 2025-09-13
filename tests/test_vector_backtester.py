import numpy as np


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def rank_and_score(
    query: np.ndarray, analogs: np.ndarray, scores: np.ndarray
) -> tuple[np.ndarray, float]:
    sims = np.array([cosine(query, v) for v in analogs])
    order = np.argsort(sims)[::-1]
    weighted = np.average(scores[order[:2]], weights=sims[order[:2]])
    return order, float(weighted)


def test_analog_ranking_and_replay_scoring():
    history = np.array([[1, 0], [0, 1], [0.8, 0.2]])
    scores = np.array([0.9, 0.1, 0.5])
    query = np.array([0.9, 0.1])
    order, score = rank_and_score(query, history, scores)
    assert order[0] == 0
    assert score > 0.7
