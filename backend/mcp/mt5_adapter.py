try:
    import MetaTrader5 as mt5
except Exception:
    mt5 = None


def init_mt5():
    """Initialize connection to MetaTrader5."""
    if mt5 is None:
        return False
    if not mt5.initialize():
        raise RuntimeError("MetaTrader5 initialization failed")
    print("MT5 bridged.")
    return True


__all__ = ["init_mt5"]
