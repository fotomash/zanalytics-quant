import asyncio
from mt5_redis_integration import MT5RedisIntegration
import MetaTrader5 as mt5

if __name__ == "__main__":
    mt5_redis = MT5RedisIntegration()
    if mt5_redis.connect_mt5():
        symbols = ['EURUSD', 'GBPUSD', 'USDJPY']
        timeframes = [mt5.TIMEFRAME_M1, mt5.TIMEFRAME_M5, mt5.TIMEFRAME_H1]
        indicators = {
            'SMA': {'period': 20},
            'RSI': {'period': 14}
        }
        try:
            asyncio.run(mt5_redis.run_data_pipeline(symbols, timeframes, indicators))
        except KeyboardInterrupt:
            print("Shutting down...")
        finally:
            mt5_redis.disconnect_mt5()
