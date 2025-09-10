# How It Works (Practical Flow)

### 1. **Data Pipeline**
- **MT5** runs inside Docker (with Wine if on Linux/Mac) and streams live tick/bar/position/order data via REST API.
- **Django/Flask** container handles user authentication, business logic, and all database ops.
- **Enrichment Scripts** (in `utils/`) transform raw market data into alpha features, rolling stats, signals, and are responsible for ETL (Extract, Transform, Load).
- **Postgres** stores all historical and enriched market data.
- **Redis** is used for real-time, super-fast caching (e.g. tickers, rolling windows).
- **Streamlit Dashboard** presents analytics and charts, pulling live from APIs or historical DB/Parquet as configured.
