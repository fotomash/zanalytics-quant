#!/usr/bin/env python3
"""
Tick-to-Bar Aggregation Service
Converts tick data from Redis streams into OHLCV bars
"""

import redis
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TickToBarService:
    def __init__(self):
        self.redis_host = os.getenv('REDIS_HOST', 'redis')
        self.redis_port = int(os.getenv('REDIS_PORT', 6379))
        self.redis_client = redis.Redis(
            host=self.redis_host, 
            port=self.redis_port, 
            decode_responses=True
        )

        # Bar configurations (in seconds)
        self.timeframes = {
            '1m': 60,
            '5m': 300,
            '15m': 900,
            '30m': 1800,
            '1h': 3600,
            '4h': 14400,
            '1d': 86400
        }

        # Storage for accumulating ticks
        self.tick_buffers = {}

    def connect(self):
        """Test Redis connection"""
        try:
            self.redis_client.ping()
            logger.info(f"Connected to Redis at {self.redis_host}:{self.redis_port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            return False

    def process_tick(self, symbol, tick_data):
        """Process a single tick and update bars"""
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

        except Exception as e:
            logger.error(f"Error processing tick: {e}")

    def _update_bar(self, symbol, timeframe, seconds, dt, price, volume):
        """Update or create a bar for the given timeframe"""
        # Calculate bar timestamp (floor to timeframe)
        bar_timestamp = dt.replace(second=0, microsecond=0)
        if timeframe in ['5m', '15m', '30m']:
            minutes = (bar_timestamp.minute // (seconds // 60)) * (seconds // 60)
            bar_timestamp = bar_timestamp.replace(minute=minutes)
        elif timeframe in ['1h', '4h']:
            hours = (bar_timestamp.hour // (seconds // 3600)) * (seconds // 3600)
            bar_timestamp = bar_timestamp.replace(hour=hours, minute=0)
        elif timeframe == '1d':
            bar_timestamp = bar_timestamp.replace(hour=0, minute=0)

        # Create bar key
        bar_key = f"bar:{timeframe}:{symbol}:{bar_timestamp.isoformat()}"

        # Get or create bar
        bar = self.redis_client.hgetall(bar_key)

        if not bar:
            # Create new bar
            bar = {
                'open': price,
                'high': price,
                'low': price,
                'close': price,
                'volume': volume,
                'tick_count': 1,
                'timestamp': bar_timestamp.isoformat()
            }
        else:
            # Update existing bar
            bar['high'] = max(float(bar['high']), price)
            bar['low'] = min(float(bar['low']), price)
            bar['close'] = price
            bar['volume'] = float(bar.get('volume', 0)) + volume
            bar['tick_count'] = int(bar.get('tick_count', 0)) + 1

        # Save bar to Redis
        self.redis_client.hset(bar_key, mapping=bar)
        self.redis_client.expire(bar_key, 86400 * 7)  # Keep for 7 days

        # Add to stream for real-time updates
        stream_key = f"stream:bar:{timeframe}:{symbol}"
        self.redis_client.xadd(stream_key, bar, maxlen=1000)

        logger.debug(f"Updated bar {bar_key}: O={bar['open']:.5f} H={bar['high']:.5f} L={bar['low']:.5f} C={bar['close']:.5f} V={bar['volume']}")

    def _publish_to_pulse(self, symbol, tick_data):
        """Publish tick to Pulse system for analysis"""
        try:
            # Publish to Pulse stream
            pulse_stream = f"stream:pulse:ticks:{symbol}"
            self.redis_client.xadd(pulse_stream, tick_data, maxlen=10000)

            # Publish to pub/sub for real-time listeners
            channel = f"pulse:ticks:{symbol}"
            self.redis_client.publish(channel, json.dumps(tick_data))

        except Exception as e:
            logger.error(f"Failed to publish to Pulse: {e}")

    def listen_for_ticks(self, symbols=None):
        """Listen for tick data from multiple sources"""
        if symbols is None:
            symbols = ['EURUSD', 'GBPUSD', 'XAUUSD']

        logger.info(f"Starting tick listener for symbols: {symbols}")

        # Create stream keys
        streams = {f"tick:{symbol}": '0' for symbol in symbols}

        while True:
            try:
                # Read from multiple streams
                messages = self.redis_client.xread(streams, block=1000, count=100)

                for stream_name, stream_messages in messages:
                    symbol = stream_name.split(':')[1]

                    for message_id, data in stream_messages:
                        logger.debug(f"Processing tick for {symbol}: {data}")
                        self.process_tick(symbol, data)

                        # Update stream position
                        streams[stream_name] = message_id

            except KeyboardInterrupt:
                logger.info("Shutting down tick-to-bar service...")
                break
            except Exception as e:
                logger.error(f"Error in tick listener: {e}")
                time.sleep(1)

    def run(self):
        """Main service loop"""
        logger.info("Starting Tick-to-Bar Service...")

        if not self.connect():
            logger.error("Cannot start service without Redis connection")
            return

        # Get symbols from environment or use defaults
        symbols = os.getenv('SYMBOLS', 'EURUSD,GBPUSD,XAUUSD').split(',')

        # Start listening
        self.listen_for_ticks(symbols)

if __name__ == "__main__":
    service = TickToBarService()
    service.run()
