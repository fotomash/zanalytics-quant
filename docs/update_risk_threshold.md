# Updating the Risk Threshold

The prediction cron uses a risk threshold to decide when a silence or spike
is significant. At startup `scripts/predict_cron.py` calls
`get_risk_threshold()` to load this value and passes it to `process_tick`.
The threshold can be supplied with the `RISK_THRESHOLD` environment variable
or stored in `config/predict_cron.yaml`.

After running backtests you can compute a recommended value from historical
data:

```bash
python scripts/predict_cron.py --history path/to/history.csv
```

The helper prints the suggested threshold. Update the environment variable
or edit `config/predict_cron.yaml` with the new value before re-running the
cron.
