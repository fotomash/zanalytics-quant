# Financial Market Data API Schema

## Endpoint

- **GET** `/market/summary`

### Query Parameters

- `assets` (string, optional): Comma-separated asset symbols (default: BTC,ETH,SP500,FTSE,NASDAQ,DOW,GOLD,OIL)
- `days` (integer, optional): Number of days for historical data (default: 180)

### Response

- `timestamp` (string): ISO8601 timestamp
- `summary` (string): Market summary text
- `data_points` (array): List of asset summaries
  - `asset` (string): Asset name and symbol
  - `price` (number): Latest price
  - `change_percent` (number): % change from previous close
  - `recommendation` (string): Buy/Sell
  - `volatility` (number): 30-day annualized volatility (%)
- `visualization`
  - `table_markdown` (string): Markdown table of summary
  - `chart_image_base64` (string): Base64 PNG of correlation heatmap
- `next_steps`
  - `immediate` (array): Immediate follow-up actions
  - `user_options` (array): User-selectable options
  - `data_refresh` (string): Data refresh interval

## Future Work

- Include full technical indicators such as RSI and MACD, along with options Greeks, in the asset summaries.
