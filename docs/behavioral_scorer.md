# Behavioral Scorer

The behavioral scorer service consumes trader activity events and maintains simple metrics in Redis. These metrics power the behavioral gates and dashboard modules.

## Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `KAFKA_BROKER` | `kafka:9092` | Kafka bootstrap servers for analysis and trade topics. |
| `REDIS_HOST` | `redis` | Hostname of the Redis instance that stores scores. |
| `REDIS_PORT` | `6379` | Redis port. |
| `SCORE_INTERVAL` | `60` | Seconds between score flushes to Redis. |
| `BEHAVIORAL_GROUP` | `behavioral-scorer` | Consumer group id. |
| `RAPID_TRADE_WINDOW` | `60` | Sliding window in seconds for rapid trade detection. |
| `RAPID_TRADE_THRESHOLD` | `3` | Number of trades in the window that trigger a rapid trade flag. |
| `PATIENCE_PENALTY` | `0.1` | Deduction applied to the patience index when rapid trading occurs. |

## Redis keys

Scores are written under the key pattern:

```
behavioral_metrics:{trader_id}
```

Each value is a JSON document containing the current metrics for that trader.

## Score payload

The payload stored for each trader has the structure:

```json
{
  "last_trade": <unix timestamp>,
  "analysis_count": <int>,
  "inactive_seconds": <float>,
  "patience_index": <float 0-1>,
  "rapid_trades": <bool>
}
```

- `last_trade` – time of the most recent trade execution.
- `analysis_count` – number of analysis events received.
- `inactive_seconds` – seconds since the last trade; `null` if the trader has not traded.
- `patience_index` – decreases by `PATIENCE_PENALTY` when more than `RAPID_TRADE_THRESHOLD` trades occur within `RAPID_TRADE_WINDOW` seconds.
- `rapid_trades` – `true` when rapid trading is detected.

## Configuration flags

Dashboard behavior and gating can be tuned through `pulse_dashboard_config.yaml`:

```yaml
behavioral_modules:
  revenge_trading: true
  overconfidence: true
  fatigue_detection: true
  fomo_protection: true
  loss_chasing: true
  time_of_day: true
```

Each flag enables a module that interprets the metrics above. Risk thresholds (for example, `risk_limits.min_confluence_score` or `risk_limits.overconfidence_threshold`) use these scores to drive warnings and cooldowns.
