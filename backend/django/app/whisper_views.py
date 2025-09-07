from __future__ import annotations

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .whisper_runtime import latest_whispers, ack_whisper, act_on_whisper


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

