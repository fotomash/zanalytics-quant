from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json
import pandas as pd

from components.wyckoff_scorer import WyckoffScorer

scorer = WyckoffScorer()


@csrf_exempt
@require_http_methods(["POST"])
def wyckoff_score(request):
    """Score Wyckoff phases and events from bar data."""
    try:
        payload = json.loads(request.body)
        df = pd.DataFrame(payload["bars"])
        if "ts" in df:
            df.set_index(pd.to_datetime(df["ts"]), inplace=True)
            df.drop(columns=["ts"], inplace=True)
        out = scorer.score(df)
        return JsonResponse(
            {
                "score": out["wyckoff_score"],
                "probs": out["wyckoff_probs"].tolist(),
                "events": {k: list(map(bool, v[-50:])) for k, v in out["events"].items()},
                "explain": out.get("explain"),
            }
        )
    except Exception as e:  # pragma: no cover - error path
        return JsonResponse({"error": str(e)}, status=400)


@require_http_methods(["GET"])
def wyckoff_health(_req):
    return JsonResponse({"status": "ok", "module": "wyckoff"})
