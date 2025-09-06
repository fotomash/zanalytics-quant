import json
from django.http import JsonResponse
from pulse.kernel import PulseKernel

kernel = PulseKernel()

def score_peek(_):
    out = kernel.peek_score()
    return JsonResponse(out, safe=False)

def score_post(request):
    payload = json.loads(request.body)
    out = kernel.process_tick(payload)
    return JsonResponse(out, safe=False)

def risk_summary(_):
    return JsonResponse(kernel.risk_enforcer.summary(), safe=False)

def signals_top(request):
    n = int(request.GET.get("n", 3))
    return JsonResponse(kernel.top_signals(n), safe=False)

def journal_recent(request):
    limit = int(request.GET.get("limit", 10))
    return JsonResponse(kernel.journal.recent(limit), safe=False)
