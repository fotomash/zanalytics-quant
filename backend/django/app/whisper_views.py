from __future__ import annotations

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .whisper_runtime import latest_whispers, ack_whisper, act_on_whisper, _redis


def whisper_stream(request):
    return JsonResponse({"whispers": latest_whispers(limit=50)})


@csrf_exempt
def whisper_ack(request):
    res = ack_whisper(request.body or b"{}")
    return JsonResponse(res)


@csrf_exempt
def whisper_act(request):
    res = act_on_whisper(request.body or b"{}")
    return JsonResponse(res)


def whisper_log(request):
    """Return combined human-readable whisper log (acks + acts)."""
    r = _redis()
    out = []
    if r is None:
        return JsonResponse({"log": out})
    try:
        items = r.lrange("whisper-log", -200, -1) or []
        import json as _json
        for b in items:
            try:
                out.append(_json.loads(b))
            except Exception:
                continue
    except Exception:
        out = []
    return JsonResponse({"log": out})
