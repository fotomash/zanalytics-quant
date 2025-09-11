from typing import List


def embed(text: str) -> List[float]:
    """Return a dummy fixed-size embedding for the given text."""
    return [0.0] * 8
