# Changelog

## [Unreleased]
### Added
- Added `__version__` constant to `pulse_kernel` and documented that Redis failures are logged without halting the pipeline for improved resilience.
- Added vector search dependencies `sentence-transformers`, `pinecone-client`, and `faiss-cpu` (use `faiss-gpu` for CUDA environments).
- Introduced `tick-to-bar` container for real-time aggregation of tick streams into OHLCV bars for downstream consumers.
- Added `predict-cron` container running scheduled risk scoring jobs that publish high-risk alerts and queue simulations.
- Added `pulse-api` container bundling Pulse kernel and risk enforcer behind an HTTP API for external integrations.
- Introduced `ticktobar` container, a lightweight Redis/Kafka bar aggregator for simple deployments.
### Changed
- Tick streams default to versioned prefix `v2:`; update consumers to read from `v2:ticks:*`.
