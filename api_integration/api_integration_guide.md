# ZANFLOW API Integration Guide

## Overview

This guide explains how to transition your dashboards from using parquet files to using the Django API for data access. The API provides access to:

- Bar data (OHLCV)
- Tick data
- Trade data
- Market orders and position management
All requests require token authentication. The token is sent in the `Authorization` header.

## Prerequisites

1. Ensure the Django backend is running and accessible
2. Obtain your API token from the Django server (token authentication is required)
3. Update your environment variables or Streamlit secrets with the API URL and token
4. Install required Python packages:
   - `requests`
   - `pandas`
   - `streamlit` (for Streamlit dashboards)

## Step 1: Set Up Environment Variables

Make sure your `.env` file or environment has the following variables:

```
DJANGO_API_URL=http://django:8000  # Replace with your actual Django API URL
DJANGO_API_TOKEN=your-token-here  # Required API token
```

For Streamlit dashboards, you can also add this to your `.streamlit/secrets.toml` file:

```toml
DJANGO_API_URL = "http://django:8000"
DJANGO_API_TOKEN = "your-token-here"
```
The API requires this token for all requests. The client will send it in the Authorization header automatically.

## Step 2: Add the API Client Files

Copy these files to your project:

1. `django_api_client.py` - The base API client
2. `zanflow_api_data_loader.py` - The data loader that replaces parquet file loading

## Step 3: Update Your Dashboards

### For Python Scripts

Replace parquet file loading code like this:

```python
# Old code - Parquet loading
df = pd.read_parquet("path/to/data.parquet")
```

With API-based loading:

```python
# New code - API loading
from zanflow_api_data_loader import ZanflowAPIDataLoader

data_loader = ZanflowAPIDataLoader()
df = data_loader.load_latest_data(symbol="XAUUSD", timeframe="1h")
```

### For Streamlit Dashboards

Replace parquet file loading code like this:

```python
# Old code - Parquet loading
@st.cache_data
def load_data():
    return pd.read_parquet("path/to/data.parquet")

df = load_data()
```

With API-based loading:

```python
# New code - API loading
from zanflow_api_data_loader import ZanflowAPIDataLoader

@st.cache_resource
def get_data_loader():
    return ZanflowAPIDataLoader()

data_loader = get_data_loader()
df = data_loader.load_latest_data(symbol="XAUUSD", timeframe="1h")
```

## Step 4: Handling Tick Data

For tick data, replace code like:

```python
# Old code - Parquet tick data
tick_df = pd.read_parquet("path/to/ticks.parquet")
```

With:

```python
# New code - API tick data
tick_df = data_loader.load_tick_data(symbol="XAUUSD", limit=10000)
```

## Step 5: Working with Trades

For trade data, use:

```python
# Get all trades
trades_df = data_loader.load_trades(limit=100)

# Get trades for a specific symbol
symbol_trades_df = data_loader.load_trades(symbol="XAUUSD", limit=50)
```

## Step 6: Sending Orders

To send market orders:

```python
# Import the client directly for order operations
from django_api_client import DjangoAPIClient

client = DjangoAPIClient()
result = client.send_market_order(
    symbol="XAUUSD",
    volume=0.01,
    order_type=0,  # 0 for buy, 1 for sell
    sl=1800.0,
    tp=1900.0
)
print(result)
```
## Core API Endpoints

- `/api/ping/` - Health check endpoint, returns `{ "status": "ok" }`
- `/api/v1/symbols/` - List available trading symbols
- `/api/v1/timeframes/` - List supported timeframes

## Example Dashboard

See `streamlit_api_dashboard.py` for a complete example of a dashboard that uses the API instead of parquet files.

## Troubleshooting

### API Connection Issues

If you're having trouble connecting to the API:

1. Check that the Django server is running
2. Verify the API URL is correct in your environment variables
3. Test the `/api/v1/ping/` endpoint to make sure the server responds with `{ "status": "ok" }`
4. Check for any network issues or firewalls blocking the connection
5. Look at the Django server logs for any errors

### Data Not Loading

If data isn't loading correctly:

1. Check the API endpoints in the Django server
2. Verify that the data exists in the database
3. Check for any permission issues
4. Try with a smaller limit value to see if it's a timeout issue

## Next Steps

1. Update all your dashboards to use the API
2. Implement caching strategies for better performance
3. Add error handling and fallback mechanisms
