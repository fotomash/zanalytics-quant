import os
import json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")
os.environ.setdefault("DJANGO_SECRET_KEY", "test-secret")
import django
django.setup()
from django.conf import settings
settings.ALLOWED_HOSTS.append("testserver")
from django.test import SimpleTestCase
from django.urls import reverse


class ScorePeekTests(SimpleTestCase):
    def test_score_peek_with_bars(self):
        bars = [
            {"open": 1.0, "high": 1.5, "low": 0.5, "close": 1.2},
            {"open": 1.2, "high": 1.7, "low": 0.8, "close": 1.4},
            {"open": 1.4, "high": 1.6, "low": 1.1, "close": 1.3},
        ]
        resp = self.client.post(
            reverse("pulse_score_peek"),
            data=json.dumps({"bars": bars}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("score", data)
        self.assertIn("timestamp", data)

    def test_score_peek_missing_bars(self):
        resp = self.client.post(
            reverse("pulse_score_peek"),
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertIn("error", data)

