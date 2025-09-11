"""Core package for Pulse runtime components."""

from .bootstrap_engine import BootstrapEngine
from .wyckoff_analyzer import WyckoffAnalyzer

# ``smc_analyzer`` currently contains legacy code that may raise errors during
# import.  Import it lazily to avoid breaking consumers that only need the
# ``WyckoffAnalyzer`` or other utilities from this package.
try:  # pragma: no cover - best effort import
    from .smc_analyzer import SMCAnalyzer  # type: ignore
except Exception:  # pragma: no cover - if it fails we simply omit it
    SMCAnalyzer = None  # type: ignore

__all__ = [
    "pulse_kernel",
    "journal_sync",
    "BootstrapEngine",
    "WyckoffAnalyzer",
]

if SMCAnalyzer is not None:
    __all__.append("SMCAnalyzer")
