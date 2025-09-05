#!/usr/bin/env python3
"""
Tick Data Flow Test Script
Tests the complete flow from MT5 -> Redis -> Django -> Processing
"""

import requests
import redis
import json
import time
from datetime import datetime

# Configuration
MT5_API_URL = "http://localhost:5001"
DJANGO_API_URL = "http://localhost:8000"
REDIS_HOST = "localhost"
REDIS_PORT = 6379

def test_mt5_connection():
    """Test MT5 API connection"""
    print("Testing MT5 API connection...")
    try:
        response = requests.get(f"{MT5_API_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ MT5 API is healthy: {data}")
            return True
        else:
            print(f"❌ MT5 API returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Failed to connect to MT5 API: {e}")
        return False

def test_tick_data(symbol="EURUSD"):
    """Test fetching tick data from MT5"""
    print(f"\nFetching tick data for {symbol}...")
    try:
        response = requests.get(f"{MT5_API_URL}/symbol_info_tick/{symbol}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Tick data received: Bid={data.get('bid')}, Ask={data.get('ask')}")
            return data
        else:
            print(f"❌ Failed to fetch tick data: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error fetching tick data: {e}")
        return None

def test_redis_connection():
    """Test Redis connection and publish tick data"""
    print("\nTesting Redis connection...")
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        r.ping()
        print("✅ Redis connection successful")
        return r
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return None

def publish_tick_to_redis(redis_client, symbol, tick_data):
    """Publish tick data to Redis stream"""
    print(f"\nPublishing tick to Redis stream...")
    try:
        stream_key = f"tick:{symbol}"
        tick_data['timestamp'] = datetime.now().isoformat()

        # Add to Redis stream
        message_id = redis_client.xadd(stream_key, tick_data)
        print(f"✅ Published to stream {stream_key} with ID: {message_id}")

        # Also publish to pub/sub channel
        channel = f"ticks:{symbol}"
        redis_client.publish(channel, json.dumps(tick_data))
        print(f"✅ Published to channel {channel}")

        return True
    except Exception as e:
        print(f"❌ Failed to publish to Redis: {e}")
        return False

def test_django_api():
    """Test Django API connection"""
    print("\nTesting Django API...")
    try:
        response = requests.get(f"{DJANGO_API_URL}/api/v1/ping/")
        if response.status_code == 200:
            print(f"✅ Django API is accessible")
            return True
        else:
            print(f"❌ Django API returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Failed to connect to Django API: {e}")
        return False

def test_tick_to_bar_conversion(redis_client, symbol="EURUSD"):
    """Test tick to bar conversion"""
    print(f"\nTesting tick-to-bar conversion for {symbol}...")

    # Simulate multiple ticks
    print("Generating sample ticks...")
    base_price = 1.0850
    for i in range(10):
        tick = {
            'bid': base_price + (i * 0.0001),
            'ask': base_price + (i * 0.0001) + 0.0001,
            'volume': 100 + i * 10,
            'timestamp': datetime.now().isoformat()
        }

        # Add to stream
        stream_key = f"tick:{symbol}"
        redis_client.xadd(stream_key, tick)
        time.sleep(0.1)

    print("✅ Generated 10 sample ticks")

    # Check if bars are being created
    bar_key = f"bar:1m:{symbol}"
    bars = redis_client.xrange(bar_key, count=5)
    if bars:
        print(f"✅ Found {len(bars)} bars in Redis")
        for bar_id, bar_data in bars:
            print(f"  Bar {bar_id}: {bar_data}")
    else:
        print("⚠️  No bars found - tick-to-bar service may not be running")

def main():
    print("="*60)
    print("TICK DATA FLOW TEST")
    print("="*60)

    # Test MT5
    if not test_mt5_connection():
        print("\n⚠️  MT5 API is not accessible. Make sure the mt5 service is running.")
        print("Run: docker-compose up -d mt5")
        return

    # Test tick data
    tick_data = test_tick_data("EURUSD")
    if not tick_data:
        print("\n⚠️  Cannot fetch tick data. Check if MT5 terminal is connected.")
        return

    # Test Redis
    redis_client = test_redis_connection()
    if not redis_client:
        print("\n⚠️  Redis is not accessible. Make sure the redis service is running.")
        print("Run: docker-compose up -d redis")
        return

    # Publish tick to Redis
    if tick_data:
        publish_tick_to_redis(redis_client, "EURUSD", tick_data)

    # Test Django
    if not test_django_api():
        print("\n⚠️  Django API is not accessible. Check the django service.")
        print("Run: docker-compose up -d django")

    # Test tick-to-bar conversion
    test_tick_to_bar_conversion(redis_client)

    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)

    print("\nSUMMARY:")
    print("--------")
    print("If all tests passed (✅), your tick data pipeline is working.")
    print("If some tests failed (❌), follow the suggestions to fix them.")
    print("\nFor real-time monitoring, use:")
    print("  docker-compose logs -f mt5 django redis celery")

if __name__ == "__main__":
    main()
