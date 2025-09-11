from django.db import models

class Trade(models.Model):
    TRADE_TYPE_CHOICES = [
        ('BUY', 'Buy'),
        ('SELL', 'Sell'),
    ]

    CLOSING_REASON_CHOICES = [
        ('TP', 'Take Profit'),
        ('SL', 'Stop Loss'),
        ('MANUAL', 'Manual'),
        ('LIQUIDATION', 'Liquidation'),
        ('OTHER', 'Other'),
    ]

    MARKET_TYPE_CHOICES = [
        ('FOREX', 'Forex'),
        ('CRYPTO', 'Crypto'),
        ('OTHER', 'Other'),
    ]

    TIMEFRAME_CHOICES = [
        ('1M', '1 Minute'),
        ('5M', '5 Minutes'),
        ('15M', '15 Minutes'),
        ('1H', '1 Hour'),
        ('4H', '4 Hours'),
        ('1D', '1 Day'),
    ]

    # Core trade fields
    transaction_broker_id = models.CharField(max_length=100)
    symbol = models.CharField(max_length=10)
    entry_time = models.DateTimeField()
    entry_price = models.FloatField()
    type = models.CharField(max_length=4, choices=TRADE_TYPE_CHOICES)
    position_size_usd = models.FloatField()
    capital = models.FloatField()
    leverage = models.FloatField(default=500)
    order_volume = models.FloatField(null=True, blank=True)
    liquidity_price = models.FloatField()
    break_even_price = models.FloatField()
    order_commission = models.FloatField()

    # Closing details
    close_time = models.DateTimeField(null=True, blank=True)
    close_price = models.FloatField(null=True, blank=True)
    pnl = models.FloatField(null=True, blank=True)
    pnl_excluding_commission = models.FloatField(null=True, blank=True)
    max_drawdown = models.FloatField(null=True, blank=True)
    max_profit = models.FloatField(null=True, blank=True)
    closing_reason = models.CharField(max_length=50, null=True, blank=True, choices=CLOSING_REASON_CHOICES)

    # Additional Info
    strategy = models.CharField(max_length=50)
    broker = models.CharField(max_length=50)
    market_type = models.CharField(max_length=50, choices=MARKET_TYPE_CHOICES)
    timeframe = models.CharField(max_length=50, choices=TIMEFRAME_CHOICES)

    def __str__(self):
        return f"{self.type} {self.symbol} at {self.entry_price}"


class TradeClosePricesMutation(models.Model):
    trade = models.ForeignKey(Trade, on_delete=models.CASCADE, related_name='close_prices_mutations')
    mutation_time = models.DateTimeField(auto_now_add=True)
    mutation_price = models.FloatField(null=True, blank=True)
    new_tp_price = models.FloatField(null=True, blank=True)
    new_sl_price = models.FloatField(null=True, blank=True)
    pnl_at_new_tp_price = models.FloatField(null=True, blank=True)
    pnl_at_new_sl_price = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ['mutation_time']
        verbose_name = "Trade Close Prices Mutation"
        verbose_name_plural = "Trade Close Prices Mutations"

    def __str__(self):
        return f"Mutation for {self.trade} at {self.mutation_time}"


class Tick(models.Model):
    symbol = models.CharField(max_length=12)
    time = models.DateTimeField(db_index=True)
    bid = models.FloatField()
    ask = models.FloatField()
    last = models.FloatField(null=True, blank=True)
    volume = models.FloatField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["symbol", "time"])]
        ordering = ["-time"]

    def __str__(self):
        return f"{self.symbol} tick @ {self.time}"


class Bar(models.Model):
    symbol = models.CharField(max_length=12)
    timeframe = models.CharField(max_length=10)
    time = models.DateTimeField(db_index=True)
    open = models.FloatField()
    high = models.FloatField()
    low = models.FloatField()
    close = models.FloatField()
    tick_volume = models.IntegerField()
    spread = models.IntegerField()
    real_volume = models.IntegerField()

    class Meta:
        indexes = [models.Index(fields=["symbol", "timeframe", "time"])]
        ordering = ["-time"]

    def __str__(self):
        return f"{self.symbol} {self.timeframe} bar @ {self.time}"


class PsychologicalState(models.Model):
    STATE_CHOICES = [
        ("CALM", "Calm"),
        ("ALERT", "Alert"),
        ("DANGER", "Danger"),
    ]

    trade = models.ForeignKey(Trade, on_delete=models.CASCADE, related_name='psychological_states')
    timestamp = models.DateTimeField(auto_now_add=True)
    state = models.CharField(max_length=10, choices=STATE_CHOICES)
    behavioral_score = models.IntegerField()

    revenge_trading_detected = models.BooleanField(default=False)
    overconfidence_detected = models.BooleanField(default=False)
    fatigue_detected = models.BooleanField(default=False)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.state} ({self.behavioral_score}) for Trade {self.trade_id}"


class JournalEntry(models.Model):
    trade = models.OneToOneField(Trade, on_delete=models.CASCADE, related_name='journal')
    pre_trade_confidence = models.IntegerField(null=True, blank=True)
    post_trade_feeling = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Journal for Trade {self.trade_id}"
