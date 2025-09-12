import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


def extract_first_number(text: Optional[str]) -> float:
    """Extract the first numeric token from *text*.

    Parameters
    ----------
    text:
        A string that is expected to contain a decimal representation of a
        number between 0.0 and 1.0. If ``None`` or if no valid number can
        be parsed, the function will return ``0.0``.

    Returns
    -------
    float
        The first number found in ``text`` as a ``float``. The value is not
        clamped but typically should fall within the inclusive range
        ``[0.0, 1.0]``. Returns ``0.0`` when ``text`` is ``None`` or lacks a
        parsable numeric token.
    """
    if text is None:
        logger.warning("extract_first_number received None; returning 0.0")
        return 0.0

    match = re.search(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", text)
    candidate = match.group(0) if match else text
    try:
        return float(candidate)
    except (TypeError, ValueError):
        logger.warning(
            "extract_first_number failed to parse float from %r; returning 0.0", text
        )
        return 0.0
