from django.test import SimpleTestCase
from app.nexus.pulse.serializers import PulseDetailSerializer


class PulseSerializerTest(SimpleTestCase):
    def test_pulse_detail_serializer_valid(self):
        payload = {
            "structure": {"passed": True, "direction": "bullish"},
            "liquidity": {"passed": False},
            "wyckoff": {"passed": True, "phase": "accumulation?", "direction": "bullish?"},
            "risk": {"used_pct": 0.2, "exposure_pct": 0.1, "target_amount": 2000.0, "loss_amount": 10000.0},
            "confluence": {"confidence": 0.6, "passed": True},
        }
        ser = PulseDetailSerializer(data=payload)
        self.assertTrue(ser.is_valid(), ser.errors)

