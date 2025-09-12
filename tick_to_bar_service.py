#!/usr/bin/env python3
"""
Tick-to-Bar Aggregation Service
Converts tick data from Redis streams into OHLCV bars
"""

import redis
import json
from datetime import datetime, timedelta
import time
import os
import logging
from confluent_kafka import Consumer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

VERSION_PREFIX = os.getenv("STREAM_VERSION_PREFIX", "v2")

class TickToBarService:
    def __init__(self):
        self.redis_host = os.getenv('REDIS_HOST', 'redis')
        self.redis_port = int(os.getenv('REDIS_PORT', 6379))
        self.redis_client = redis.Redis(
            host=self.redis_host, 
            port=self.redis_port, 
            decode_responses=True
        )

        # All available timeframe configurations (in seconds)
        self.available_timeframes = {
            '1m': 60,
            '5m': 300,
            '15m': 900,
            '30m': 1800,
            '1h': 3600,
            '4h': 14400,
            '1d': 86400,
        }

        # Active timeframes - can be overridden in run()
        self.timeframes = dict(self.available_timeframes)

        # In-memory bar states {(timeframe, symbol): bar_dict}
        self.bar_states = {}

    def connect(self):
        """Test Redis connection"""
        try:
            self.redis_client.ping()
            logger.info(f"Connected to Redis at {self.redis_host}:{self.redis_port}")
            return True
        except Exception:
            logger.exception("Failed to connect to Redis")
            return False

    def process_tick(self, symbol, tick_data, topic=None, key=None):
        """Process a single tick and update bars.

        Parameters
        ----------
        symbol: str
            Symbol for the tick.
        tick_data: dict
            Raw tick dictionary.
        topic: Optional[str]
            Kafka topic from which the tick was read.
        key: Optional[str]
            Kafka key associated with the tick.
        """

        try:
            # Parse tick data
            bid = float(tick_data.get('bid', 0))
            ask = float(tick_data.get('ask', 0))
            volume = float(tick_data.get('volume', 0))
            timestamp = tick_data.get('timestamp', datetime.now().isoformat())

            # Use mid price for OHLC
            price = (bid + ask) / 2

            # Convert timestamp to datetime
            if isinstance(timestamp, str):
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            else:
                dt = datetime.fromtimestamp(float(timestamp))

            # Update bars for each timeframe
            for tf_name, tf_seconds in self.timeframes.items():
                self._update_bar(symbol, tf_name, tf_seconds, dt, price, volume)

            # Publish to Pulse system
            self._publish_to_pulse(symbol, tick_data)

        except Exception:
            logger.exception(
                "Error processing tick: topic=%s key=%s tick=%s",
                topic,
                key,
                tick_data,
            )

    def _update_bar(self, symbol, timeframe, seconds, dt, price, volume):
        """Update or create a bar for the given timeframe"""

        # Determine the start time for the bar by flooring the timestamp
        bar_timestamp = dt.replace(second=0, microsecond=0)
        if timeframe in ['5m', '15m', '30m']:
            minutes = (bar_timestamp.minute // (seconds // 60)) * (seconds // 60)
            bar_timestamp = bar_timestamp.replace(minute=minutes)
        elif timeframe in ['1h', '4h']:
            hours = (bar_timestamp.hour // (seconds // 3600)) * (seconds // 3600)
            bar_timestamp = bar_timestamp.replace(hour=hours, minute=0)
        elif timeframe == '1d':
            bar_timestamp = bar_timestamp.replace(hour=0, minute=0)

        state_key = (timeframe, symbol)
        bar = self.bar_states.get(state_key)

        if not bar or bar['timestamp'] != bar_timestamp:
            # Start a new bar
            bar = {
                'open': price,
                'high': price,
                'low': price,
                'close': price,
                'volume': volume,
                'tick_count': 1,
                'timestamp': bar_timestamp,
            }
        else:
            # Update existing bar
            bar['high'] = max(bar['high'], price)
            bar['low'] = min(bar['low'], price)
            bar['close'] = price
            bar['volume'] += volume
            bar['tick_count'] += 1

        # Persist bar state
        self.bar_states[state_key] = bar
        self._persist_bar(symbol, timeframe, bar)

        logger.debug(
            f"Updated bar {timeframe}:{symbol}:{bar_timestamp.isoformat()}: "
            f"O={bar['open']:.5f} H={bar['high']:.5f} L={bar['low']:.5f} C={bar['close']:.5f} V={bar['volume']}"
        )

    def _persist_bar(self, symbol, timeframe, bar):
        """Persist the bar to Redis hash and stream"""
        bar_data = {
            'open': bar['open'],
            'high': bar['high'],
            'low': bar['low'],
            'close': bar['close'],
            'volume': bar['volume'],
            'tick_count': bar['tick_count'],
            'timestamp': bar['timestamp'].isoformat(),
        }

        bar_key = f"bar:{timeframe}:{symbol}:{bar_data['timestamp']}"
        self.redis_client.hset(bar_key, mapping=bar_data)
        self.redis_client.expire(bar_key, 86400 * 7)

        stream_key = f"stream:bar:{timeframe}:{symbol}"
        self.redis_client.xadd(stream_key, bar_data, maxlen=1000)

    def _publish_to_pulse(self, symbol, tick_data):
        """Publish tick to Pulse system for analysis"""
        try:
            # Publish to Pulse stream
            pulse_stream = f"stream:pulse:ticks:{symbol}"
            self.redis_client.xadd(pulse_stream, tick_data, maxlen=10000)

            # Publish to pub/sub for real-time listeners
            channel = f"pulse:ticks:{symbol}"
            self.redis_client.publish(channel, json.dumps(tick_data))

        except Exception:
            logger.exception("Failed to publish to Pulse: symbol=%s tick=%s", symbol, tick_data)

    def listen_for_ticks(self, symbols=None):
        """Listen for tick data from multiple sources"""
        if symbols is None:
            symbols = ['EURUSD', 'GBPUSD', 'XAUUSD']

        logger.info(f"Starting tick listener for symbols: {symbols}")

        # Create stream keys
        streams = {f"{VERSION_PREFIX}:ticks:{symbol}": '0' for symbol in symbols}

        while True:
            try:
                # Read from multiple streams
                messages = self.redis_client.xread(streams, block=1000, count=100)

                for stream_name, stream_messages in messages:
                    symbol = stream_name.split(':')[-1]

                    for message_id, data in stream_messages:
                        logger.debug(f"Processing tick for {symbol}: {data}")
                        self.process_tick(symbol, data)

                        # Update stream position
                        streams[stream_name] = message_id

            except KeyboardInterrupt:
                logger.info("Shutting down tick-to-bar service...")
                break
            except Exception:
                logger.exception("Error in tick listener")
                time.sleep(1)

    def listen_for_ticks_kafka(self, symbols=None):
        """Consume ticks from Kafka and process them."""
        conf = {
            "bootstrap.servers": os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
            "group.id": os.getenv("KAFKA_GROUP_ID", "tick-to-bar"),
            "auto.offset.reset": "earliest",
        }
        topic = os.getenv("KAFKA_TICKS_TOPIC", "mt5.ticks")
        consumer = Consumer(conf)
        consumer.subscribe([topic])
        try:
            while True:
                msg = consumer.poll(1.0)
                if msg is None:
                    continue
                if msg.error():
                    logger.error(f"Kafka error: {msg.error()}")
                    continue
                raw_value = msg.value()
                try:
                    data = json.loads(raw_value)
                    symbol = data.get("symbol")
                    if symbol:
                        self.process_tick(
                            symbol,
                            data,
                            topic=msg.topic(),
                            key=msg.key(),
                        )
                except Exception:
                    logger.exception(
                        "Failed processing Kafka message: topic=%s key=%s tick=%s",
                        msg.topic(),
                        msg.key(),
                        raw_value,
                    )
        except KeyboardInterrupt:
            logger.info("Shutting down tick-to-bar service...")
        finally:
            consumer.close()

    def run(self, symbols=None, timeframes=None):
        """Main service loop.

        Parameters
        ----------
        symbols : Optional[List[str]]
            Symbols to subscribe to. Defaults to environment variable ``SYMBOLS``.
        timeframes : Optional[List[str]]
            List of timeframe names (e.g., ["1m", "5m"]) to aggregate.
            If omitted, all available timeframes are used.
        """

        logger.info("Starting Tick-to-Bar Service...")

        if timeframes:
            self.timeframes = {
                tf: self.available_timeframes[tf]
                for tf in timeframes
                if tf in self.available_timeframes
            }
            logger.info(f"Configured timeframes: {list(self.timeframes.keys())}")

        if not self.connect():
            logger.error("Cannot start service without Redis connection")
            return

        if symbols is None:
            symbols = os.getenv('SYMBOLS', 'EURUSD,GBPUSD,XAUUSD').split(',')

        # Start listening via Kafka
        self.listen_for_ticks_kafka(symbols)

if __name__ == "__main__":
    service = TickToBarService()
    service.run()
