import MetaTrader5 as mt5
import redis
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd

from metadata import indicator_registry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MT5RedisIntegration:
    """Stream MT5 data to Redis."""

    def __init__(self, redis_host: str = 'localhost', redis_port: int = 6379, redis_db: int = 0):
        self.redis_client = redis.Redis(host=redis_host, port=redis_port, db=redis_db, decode_responses=True)
        self.redis_stream = redis.Redis(host=redis_host, port=redis_port, db=redis_db)
        self.symbols: List[str] = []
        self.is_connected = False
        # Publish indicator metadata so consumers can cache it.
        try:
            indicator_registry.publish_registry(redis_client=self.redis_client)
        except Exception as exc:  # pragma: no cover - publication is best effort
            logger.warning("Failed to publish indicator metadata: %s", exc)

    def connect_mt5(self) -> bool:
        if not mt5.initialize():
            logger.error(f"MT5 initialization failed: {mt5.last_error()}")
            return False
        self.is_connected = True
        logger.info("Connected to MT5")
        return True

    def disconnect_mt5(self):
        mt5.shutdown()
        self.is_connected = False
        logger.info("Disconnected from MT5")

    def set_symbols(self, symbols: List[str]):
        self.symbols = symbols
        for symbol in symbols:
            mt5.symbol_select(symbol, True)

    async def stream_live_data(self):
        while self.is_connected:
            try:
                for symbol in self.symbols:
                    tick = mt5.symbol_info_tick(symbol)
                    if tick:
                        tick_data = {
                            'symbol': symbol,
                            'time': tick.time,
                            'bid': tick.bid,
                            'ask': tick.ask,
                            'last': tick.last,
                            'volume': tick.volume,
                            'timestamp': datetime.now().isoformat()
                        }
                        stream_key = f"tick_stream:{symbol}"
                        self.redis_stream.xadd(stream_key, tick_data, maxlen=10000)
                        self.redis_client.setex(f"latest_tick:{symbol}", 300, json.dumps(tick_data))
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Error streaming data: {e}")
                await asyncio.sleep(1)

    def cache_historical_data(self, symbol: str, timeframe: int, count: int = 1000) -> pd.DataFrame:
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
        if rates is None:
            logger.error(f"Failed to get rates for {symbol}")
            return pd.DataFrame()
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        cache_key = f"ohlc:{symbol}:{timeframe}"
        data = {
            'data': df.to_json(orient='records'),
            'last_update': datetime.now().isoformat(),
            'count': len(df)
        }
        self.redis_client.setex(cache_key, 3600, json.dumps(data))
        logger.info(f"Cached {len(df)} bars for {symbol} TF:{timeframe}")
        return df

    def get_cached_data(self, symbol: str, timeframe: int) -> Optional[pd.DataFrame]:
        cached = self.redis_client.get(f"ohlc:{symbol}:{timeframe}")
        if cached:
            data = json.loads(cached)
            df = pd.read_json(data['data'])
            df['time'] = pd.to_datetime(df['time'])
            return df
        return None

    def stream_indicators(self, symbol: str, timeframe: int, indicators: Dict[str, Dict]):
        df = self.get_cached_data(symbol, timeframe)
        if df is None or df.empty:
            df = self.cache_historical_data(symbol, timeframe)
        if df.empty:
            return
        values: Dict[int, float] = {}
        for ind_name, params in indicators.items():
            if ind_name == 'SMA':
                period = params.get('period', 20)
                df[f'SMA_{period}'] = df['close'].rolling(window=period).mean()
                reg_id = indicator_registry.get_id(f'SMA_{period}')
                if reg_id is not None:
                    values[reg_id] = float(df[f'SMA_{period}'].iloc[-1])
            elif ind_name == 'RSI':
                period = params.get('period', 14)
                delta = df['close'].diff()
                gain = delta.where(delta > 0, 0).rolling(window=period).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
                rs = gain / loss
                df[f'RSI_{period}'] = 100 - (100 / (1 + rs))
                reg_id = indicator_registry.get_id(f'RSI_{period}')
                if reg_id is not None:
                    values[reg_id] = float(df[f'RSI_{period}'].iloc[-1])
        indicator_data = {'symbol': symbol, 'timeframe': timeframe}
        indicator_data.update({str(k): v for k, v in values.items()})
        self.redis_stream.xadd(f"indicator_stream:{symbol}:{timeframe}", indicator_data, maxlen=1000)
        self.redis_client.setex(
            f"latest_indicators:{symbol}:{timeframe}",
            300,
            json.dumps({'symbol': symbol, 'timeframe': timeframe, 'indicators': values}),
        )

    def get_account_info(self) -> Dict:
        info = mt5.account_info()
        if info is None:
            return {}
        account = {
            'balance': info.balance,
            'equity': info.equity,
            'margin': info.margin,
            'free_margin': info.margin_free,
            'profit': info.profit,
            'currency': info.currency,
            'leverage': info.leverage,
            'timestamp': datetime.now().isoformat()
        }
        self.redis_client.setex('account_info', 60, json.dumps(account))
        return account

    def get_open_positions(self) -> List[Dict]:
        positions = mt5.positions_get()
        if positions is None:
            return []
        result = []
        for pos in positions:
            data = {
                'ticket': pos.ticket,
                'symbol': pos.symbol,
                'type': 'BUY' if pos.type == 0 else 'SELL',
                'volume': pos.volume,
                'price_open': pos.price_open,
                'price_current': pos.price_current,
                'profit': pos.profit,
                'sl': pos.sl,
                'tp': pos.tp,
                'time': pos.time,
                'timestamp': datetime.now().isoformat()
            }
            result.append(data)
        self.redis_client.setex('open_positions', 60, json.dumps(result))
        for pos in result:
            self.redis_stream.xadd('position_stream', pos, maxlen=1000)
        return result

    async def run_data_pipeline(self, symbols: List[str], timeframes: List[int], indicators: Dict[str, Dict]):
        self.set_symbols(symbols)
        tasks = [
            asyncio.create_task(self.stream_live_data()),
            asyncio.create_task(self._update_historical_data(symbols, timeframes)),
            asyncio.create_task(self._update_indicators(symbols, timeframes, indicators)),
            asyncio.create_task(self._update_account_data()),
        ]
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            pass

    async def _update_historical_data(self, symbols: List[str], timeframes: List[int]):
        while self.is_connected:
            for symbol in symbols:
                for tf in timeframes:
                    self.cache_historical_data(symbol, tf)
            await asyncio.sleep(300)

    async def _update_indicators(self, symbols: List[str], timeframes: List[int], indicators: Dict[str, Dict]):
        while self.is_connected:
            for symbol in symbols:
                for tf in timeframes:
                    self.stream_indicators(symbol, tf, indicators)
            await asyncio.sleep(60)

    async def _update_account_data(self):
        while self.is_connected:
            self.get_account_info()
            self.get_open_positions()
            await asyncio.sleep(10)

if __name__ == "__main__":
    mt5_redis = MT5RedisIntegration()
    if mt5_redis.connect_mt5():
        import MetaTrader5 as mt5
        symbols = ['EURUSD', 'GBPUSD', 'USDJPY']
        timeframes = [mt5.TIMEFRAME_M1, mt5.TIMEFRAME_M5, mt5.TIMEFRAME_H1]
        indicators = {
            'SMA': {'period': 20},
            'RSI': {'period': 14},
        }
        try:
            asyncio.run(mt5_redis.run_data_pipeline(symbols, timeframes, indicators))
        except KeyboardInterrupt:
            pass
        finally:
            mt5_redis.disconnect_mt5()
