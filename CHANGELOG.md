# Changelog

## [Unreleased]
### Added
- Added `__version__` constant to `pulse_kernel` and documented that Redis failures are logged without halting the pipeline for improved resilience.
### Changed
- Tick streams default to versioned prefix `v2:`; update consumers to read from `v2:ticks:*`.
