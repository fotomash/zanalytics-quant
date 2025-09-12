# Data Enrichment & Customization

- **Modify or extend enrichment scripts** in `utils/` to calculate your own custom features.
- Run enrichment as a scheduled job, via cron, or as a service container.
- You can create new dashboards by adding new `.py` files in the `dashboard/` folder and referencing new data sources (DB, Redis, Parquet).

## Example Enrichment Workflow

A typical enrichment workflow begins with raw tick data streamed from MT5 or loaded from CSV/Parquet snapshots. Each tick is processed by enrichment scripts in `utils/` which perform the following steps:

1. **Transformation:** The raw tick is parsed and normalized (e.g., timestamp conversion, price adjustments).
2. **Hashing:** The tick is hashed with MD5 to detect duplicates.
3. **Storage:** Unique ticks are inserted into Postgres for long-term storage and cached in Redis for fast access.
4. **Feature Generation:** `utils/enrich.py` currently augments each tick with a Wyckoff phase label, an aggregated confidence score, a human-readable nudge, and an embedding vector. More advanced analytics are intentionally omitted for now.
5. **Caching:** Computed enrichments are cached in Redis to support low-latency dashboard queries.
6. **Visualization:** The Streamlit dashboard fetches enriched data from the Django API, which queries both Postgres and Redis, to render charts and analytics in near real-time.

This pipeline ensures that enriched data remains consistent, performant, and extensible for custom quant research.

## Future Work

- Introduce technical indicators (e.g., SMA, RSI) and options Greeks as optional enrichment modules.
