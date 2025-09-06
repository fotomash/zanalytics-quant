import sys
from types import SimpleNamespace

try:
    import MetaTrader5  # noqa: F401
except Exception:
    sys.modules['MetaTrader5'] = SimpleNamespace(
        initialize=lambda: False,
        login=lambda *a, **k: False,
        shutdown=lambda: None,
        history_deals_get=lambda *a, **k: [],
        symbol_info_tick=lambda *a, **k: None,
    )
