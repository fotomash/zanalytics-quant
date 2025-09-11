# Data Integrity and Deduplication: MD5 Flow

To ensure data integrity and prevent duplication of tick data, the platform employs an MD5 hashing mechanism as part of its enrichment and caching workflow. Each incoming tick is serialized and hashed using MD5, producing a unique fingerprint that represents the tick's content.

This MD5 hash is then used within the enrichment scripts (notably within components like `TickVectorizer`) to detect duplicate ticks before insertion into the database or cache. By comparing incoming tick hashes against existing entries in Redis or Postgres, the system avoids redundant processing and storage, which is critical for maintaining accurate real-time analytics.

This approach improves both data quality and system efficiency, ensuring that dashboards and APIs reflect consistent, deduplicated market data streams.
