import time
import MetaTrader5 as mt5


def init_mt5():
    """Initialize connection to MetaTrader5 with retries."""
    if not mt5.initialize():
        print("MT5 not ready - retrying...")
        time.sleep(5)
        return init_mt5()
    print("MT5 bridged.")


__all__ = ["init_mt5"]
