"""Thin wrapper to run TickToBarService."""
import argparse

from tick_to_bar_service import TickToBarService


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Tick-to-Bar aggregation")
    parser.add_argument(
        "--timeframes",
        nargs="+",
        help="List of desired timeframes, e.g. 1m 5m",
    )
    parser.add_argument(
        "--symbols",
        nargs="+",
        help="Symbols to process; defaults to env SYMBOLS",
    )
    args = parser.parse_args()

    TickToBarService().run(symbols=args.symbols, timeframes=args.timeframes)
