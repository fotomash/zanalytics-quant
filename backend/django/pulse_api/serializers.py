from rest_framework import serializers

ALLOWED_SYMBOLS = {"EURUSD", "XAUUSD", "BTCUSD"}


class TickQuerySerializer(serializers.Serializer):
    symbol = serializers.ChoiceField(choices=sorted(ALLOWED_SYMBOLS))
    start = serializers.DateTimeField(required=False)
    end = serializers.DateTimeField(required=False)


class SignalSerializer(serializers.Serializer):
    symbol = serializers.ChoiceField(choices=sorted(ALLOWED_SYMBOLS))
    signal = serializers.ChoiceField(choices=["BUY", "SELL", "HOLD"])
    confidence = serializers.FloatField(min_value=0, max_value=1)


class MarketDataSerializer(serializers.Serializer):
    volatility = serializers.FloatField(required=False)
    historical_volatility = serializers.FloatField(required=False)
    correlation_dxy_vix = serializers.FloatField(required=False)
    reward_risk_ratio = serializers.FloatField(required=False)


class RiskEvalSerializer(serializers.Serializer):
    signal = SignalSerializer()
    market_data = MarketDataSerializer()
