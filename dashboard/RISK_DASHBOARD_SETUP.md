# Risk Management Dashboard Setup (Retired)

> Status: Retired. This guide documents an early bootstrap for the risk
> dashboards. The current, actively maintained direction is documented in
> `docs/README.md` and the per‑page code/README files under `dashboard/pages/`.

## 1. File Placement (historical)

Place the dashboard file in your Streamlit pages directory:
```bash
cp 16_risk_manager.py dashboard/pages/
# OR for testing without MT5:
cp 16_risk_manager_mock.py dashboard/pages/16_risk_manager.py
```

## 2. Environment Configuration (historical)

Create or update your `.env` file with MT5 credentials:
```bash
cp .env.template .env
# Edit .env with your actual MT5 credentials
```

## 3. Install Required Packages

Use the shared dashboard requirements file:
```bash
pip install -r requirements/dashboard.txt
```

## 4. Access the Dashboard

1. Start your services:
```bash
docker compose up -d
```

2. Access Streamlit:
```
http://localhost:8501
```

3. Navigate to "Risk Manager" in the sidebar

## 5. Features

### Account Overview
- Real-time balance and equity monitoring
- Margin level tracking
- Daily P&L calculation
- Win rate statistics

### Risk Metrics
- Overall risk score (0-100)
- Drawdown percentage
- Account risk assessment
- Position risk analysis

### Position Management
- Live open positions table
- Profit/loss color coding
- Position details and timing

### Trade History
- Historical trade analysis
- Cumulative P&L chart
- Summary statistics
- Detailed trade logs

### Risk Warnings
- Automated risk alerts
- Drawdown warnings
- Position limit monitoring
- Daily loss tracking

## 6. Configuration Options

### Sidebar Controls
- Auto-refresh toggle
- Refresh interval adjustment
- Risk limit settings
- Display preferences

### Risk Limits (Configurable)
- Daily loss limit (%)
- Maximum drawdown (%)
- Maximum open positions
- Risk per trade (%)

## 7. Testing Without MT5

Use the mock version for testing:
```python
# This version generates random data for testing
# No MT5 connection required
python 16_risk_manager_mock.py
```

## 8. Troubleshooting

### MT5 Connection Issues
- Verify credentials in .env file
- Check MT5 server is accessible
- Ensure MetaTrader5 package is installed

### Redis Connection Issues
- Verify Redis is running: `docker compose ps redis`
- Check Redis connectivity: `docker compose exec redis redis-cli ping`

### Dashboard Not Loading
- Check Streamlit logs: `docker compose logs streamlit`
- Verify file permissions
- Ensure all dependencies are installed

## 9. Customization

### Adding Custom Metrics
Edit the `calculate_risk_metrics()` function to add your own risk calculations.

### Modifying Risk Limits
Adjust the sliders in the sidebar or set defaults in the code.

### Styling
Modify the CSS in the dashboard for custom appearance.

## 10. Integration with Pulse System

The dashboard integrates with your Pulse components:
- Reads from Redis streams
- Uses same risk limits as RiskEnforcer
- Shares metrics with PulseKernel
