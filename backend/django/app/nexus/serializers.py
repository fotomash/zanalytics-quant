from rest_framework import serializers
from .models import Trade, TradeClosePricesMutation, Tick, Bar

class TradeClosePricesMutationSerializer(serializers.ModelSerializer):
    class Meta:
        model = TradeClosePricesMutation
        fields = '__all__'

class TradeSerializer(serializers.ModelSerializer):
    close_prices_mutations = TradeClosePricesMutationSerializer(many=True, read_only=True)

    class Meta:
        model = Trade
        fields = '__all__'


class TickSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tick
        fields = '__all__'


class BarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bar
        fields = '__all__'
