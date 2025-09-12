import json
from unittest.mock import MagicMock

from services.common.redis_utils import BEHAVIORAL_SCORE_TTL, set_behavioral_score


def test_set_behavioral_score_sets_ttl():
    r = MagicMock()
    payload = {"foo": "bar"}
    set_behavioral_score(r, "trader1", payload)
    r.setex.assert_called_once_with(
        "behavioral_metrics:trader1", BEHAVIORAL_SCORE_TTL, json.dumps(payload)
    )
