from __future__ import annotations

import os
from django.http import JsonResponse


class XPulseKeyMiddleware:
    """API key middleware using X-Pulse-Key header.

    Behavior:
      - If PULSE_API_KEY is not set, this middleware is inert.
      - For unsafe methods (POST/PUT/PATCH/DELETE), require X-Pulse-Key == PULSE_API_KEY.
      - Read-only GET requests are allowed without the key.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.api_key = os.getenv("PULSE_API_KEY")

    def __call__(self, request):
        if self.api_key:
            if request.method in ("POST", "PUT", "PATCH", "DELETE"):
                key = request.headers.get("X-Pulse-Key") or request.META.get("HTTP_X_PULSE_KEY")
                if key != self.api_key:
                    return JsonResponse({"error": "Unauthorized"}, status=401)
        return self.get_response(request)

