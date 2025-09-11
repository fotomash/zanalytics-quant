# Changelog

## [Unreleased]
### Added
- Added `__version__` constant to `pulse_kernel` and documented that Redis failures are logged without halting the pipeline for improved resilience.
- Added vector search dependencies `sentence-transformers`, `pinecone-client`, and `faiss-cpu` (use `faiss-gpu` for CUDA environments).
### Changed
- Tick streams default to versioned prefix `v2:`; update consumers to read from `v2:ticks:*`.
