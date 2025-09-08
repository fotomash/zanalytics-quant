from rest_framework import serializers
from typing import Dict, Optional


class GateResultSerializer(serializers.Serializer):
    passed = serializers.BooleanField()
    direction = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    details = serializers.DictField(required=False)


class WyckoffGateSerializer(serializers.Serializer):
    passed = serializers.BooleanField()
    phase = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    direction = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class ConfluenceSerializer(serializers.Serializer):
    confidence = serializers.FloatField()
    passed = serializers.BooleanField()


class RiskEnvelopeSerializer(serializers.Serializer):
    used_pct = serializers.FloatField(required=False, allow_null=True)
    exposure_pct = serializers.FloatField(required=False, allow_null=True)
    target_amount = serializers.FloatField(required=False, allow_null=True)
    loss_amount = serializers.FloatField(required=False, allow_null=True)


class PulseDetailSerializer(serializers.Serializer):
    structure = GateResultSerializer()
    liquidity = GateResultSerializer()
    wyckoff = WyckoffGateSerializer()
    risk = RiskEnvelopeSerializer()
    confluence = ConfluenceSerializer()


class BehavioralMirrorSerializer(serializers.Serializer):
    discipline = serializers.FloatField(required=False, allow_null=True)
    patience = serializers.FloatField(required=False, allow_null=True)
    patience_ratio = serializers.FloatField(required=False, allow_null=True)
    conviction = serializers.FloatField(required=False, allow_null=True)
    efficiency = serializers.FloatField(required=False, allow_null=True)

