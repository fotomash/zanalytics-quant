# Future Directions & Next Steps

We plan to enhance the platform with the following improvements:

- **Live Data Ingestion:** Streamline MT5 data ingestion to support higher throughput and lower latency.
- **Redis-first Caching:** Shift more data queries to Redis for real-time responsiveness, reducing Postgres load.
- **Decoupling Enrichment:** Separate enrichment pipelines from the dashboard layer to allow independent scaling and scheduling.
- **Enhanced API Security:** Implement OAuth2 and token-based authentication for finer-grained access control and auditability.
- **Expanded Analytics:** Add optional modules for full technical indicators and options Greeks once core enrichment is stable.

These steps aim to improve scalability, security, and flexibility for professional quant workflows.
