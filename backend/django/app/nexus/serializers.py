from rest_framework import serializers
from .models import Trade, TradeClosePricesMutation, Tick, Bar, PsychologicalState, JournalEntry

class TradeClosePricesMutationSerializer(serializers.ModelSerializer):
    class Meta:
        model = TradeClosePricesMutation
        fields = '__all__'

class TradeSerializer(serializers.ModelSerializer):
    close_prices_mutations = TradeClosePricesMutationSerializer(many=True, read_only=True)
    journal = serializers.SerializerMethodField()
    recent_psych = serializers.SerializerMethodField()

    class Meta:
        model = Trade
        fields = '__all__'
        depth = 0

    def get_journal(self, obj):
        try:
            j = obj.journal
        except JournalEntry.DoesNotExist:
            return None
        return JournalEntrySerializer(j).data

    def get_recent_psych(self, obj):
        ps = obj.psychological_states.all().order_by('-timestamp')[:3]
        return PsychologicalStateSerializer(ps, many=True).data


class TickSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tick
        fields = '__all__'


class BarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bar
        fields = '__all__'


class PsychologicalStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PsychologicalState
        fields = '__all__'


class JournalEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = JournalEntry
        fields = '__all__'
