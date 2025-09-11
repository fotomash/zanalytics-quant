from rest_framework import serializers
from .models import Trade, TradeClosePricesMutation, Tick, Bar, PsychologicalState, JournalEntry


class TradeClosePricesMutationSerializer(serializers.ModelSerializer):
    class Meta:
        model = TradeClosePricesMutation
        fields = '__all__'


class PsychologicalStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PsychologicalState
        fields = '__all__'


class JournalEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = JournalEntry
        fields = '__all__'


class TradeSerializer(serializers.ModelSerializer):
    close_prices_mutations = TradeClosePricesMutationSerializer(many=True, read_only=True)
    psychological_states = PsychologicalStateSerializer(many=True, read_only=True)
    journal = JournalEntrySerializer(read_only=True)
    recent_psych = serializers.SerializerMethodField()

    class Meta:
        model = Trade
        fields = '__all__'
        depth = 0

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


# --- Additional lightweight serializers for Mirror/Discipline endpoints ---

class MirrorStateSerializer(serializers.Serializer):
    patience_ratio = serializers.FloatField(required=False, allow_null=True)
    discipline = serializers.FloatField(required=False, allow_null=True)
    efficiency = serializers.FloatField(required=False, allow_null=True)
    conviction_hi_win = serializers.FloatField(required=False, allow_null=True)
    conviction_lo_loss = serializers.FloatField(required=False, allow_null=True)
    pnl_norm = serializers.FloatField(required=False, allow_null=True)
    pnl_today = serializers.FloatField(required=False, allow_null=True)
    # Optional extras used by UI drawers
    discipline_deltas = serializers.ListField(child=serializers.DictField(), required=False)
    patience_median_min = serializers.FloatField(required=False, allow_null=True)
    patience_p25_min = serializers.FloatField(required=False, allow_null=True)
    patience_p75_min = serializers.FloatField(required=False, allow_null=True)


class DisciplineDaySerializer(serializers.Serializer):
    date = serializers.DateField()
    score = serializers.FloatField()


class DisciplineSummarySerializer(serializers.Serializer):
    today = serializers.FloatField(required=False, allow_null=True)
    yesterday = serializers.FloatField(required=False, allow_null=True)
    seven_day = DisciplineDaySerializer(many=True)
    events_today = serializers.ListField(child=serializers.DictField(), required=False)
