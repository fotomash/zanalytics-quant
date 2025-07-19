from flask import Blueprint, jsonify, request
import MetaTrader5 as mt5
import logging
import os
import json
from datetime import datetime
import pytz
import pandas as pd
from flasgger import swag_from
from lib import get_timeframe

try:
    import redis
except ImportError:  # pragma: no cover - optional dependency
    redis = None

data_bp = Blueprint('data', __name__)
logger = logging.getLogger(__name__)

# Optional Redis caching
redis_client = None
if redis is not None:
    try:
        redis_url = os.environ.get("REDIS_URL")
        if redis_url:
            redis_client = redis.Redis.from_url(redis_url)
        else:
            redis_host = os.environ.get("REDIS_HOST", "localhost")
            redis_port = int(os.environ.get("REDIS_PORT", 6379))
            redis_client = redis.Redis(host=redis_host, port=redis_port)
        redis_client.ping()
    except Exception:
        redis_client = None

@data_bp.route('/fetch_data_pos', methods=['GET'])
@swag_from({
    'tags': ['Data'],
    'parameters': [
        {
            'name': 'symbol',
            'in': 'query',
            'type': 'string',
            'required': True,
            'description': 'Symbol name to fetch data for.'
        },
        {
            'name': 'timeframe',
            'in': 'query',
            'type': 'string',
            'required': False,
            'default': 'M1',
            'description': 'Timeframe for the data (e.g., M1, M5, H1).'
        },
        {
            'name': 'num_bars',
            'in': 'query',
            'type': 'integer',
            'required': False,
            'default': 100,
            'description': 'Number of bars to fetch.'
        }
    ],
    'responses': {
        200: {
            'description': 'Data fetched successfully.',
            'schema': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'time': {'type': 'string', 'format': 'date-time'},
                        'open': {'type': 'number'},
                        'high': {'type': 'number'},
                        'low': {'type': 'number'},
                        'close': {'type': 'number'},
                        'tick_volume': {'type': 'integer'},
                        'spread': {'type': 'integer'},
                        'real_volume': {'type': 'integer'}
                    }
                }
            }
        },
        400: {
            'description': 'Invalid request parameters.'
        },
        404: {
            'description': 'Failed to get rates data.'
        },
        500: {
            'description': 'Internal server error.'
        }
    }
})
def fetch_data_pos_endpoint():
    """
    Fetch Data from Position
    ---
    description: Retrieve historical price data for a given symbol starting from a specific position.
    """
    try:
        symbol = request.args.get('symbol')
        timeframe = request.args.get('timeframe', 'M1')
        num_bars = int(request.args.get('num_bars', 100))
        
        if not symbol:
            return jsonify({"error": "Symbol parameter is required"}), 400

        mt5_timeframe = get_timeframe(timeframe)
        
        rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, 0, num_bars)
        if rates is None:
            return jsonify({"error": "Failed to get rates data"}), 404
        
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        
        return jsonify(df.to_dict(orient='records'))
    
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error in fetch_data_pos: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@data_bp.route('/fetch_data_range', methods=['GET'])
@swag_from({
    'tags': ['Data'],
    'parameters': [
        {
            'name': 'symbol',
            'in': 'query',
            'type': 'string',
            'required': True,
            'description': 'Symbol name to fetch data for.'
        },
        {
            'name': 'timeframe',
            'in': 'query',
            'type': 'string',
            'required': False,
            'default': 'M1',
            'description': 'Timeframe for the data (e.g., M1, M5, H1).'
        },
        {
            'name': 'start',
            'in': 'query',
            'type': 'string',
            'required': True,
            'format': 'date-time',
            'description': 'Start datetime in ISO format.'
        },
        {
            'name': 'end',
            'in': 'query',
            'type': 'string',
            'required': True,
            'format': 'date-time',
            'description': 'End datetime in ISO format.'
        }
    ],
    'responses': {
        200: {
            'description': 'Data fetched successfully.',
            'schema': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'time': {'type': 'string', 'format': 'date-time'},
                        'open': {'type': 'number'},
                        'high': {'type': 'number'},
                        'low': {'type': 'number'},
                        'close': {'type': 'number'},
                        'tick_volume': {'type': 'integer'},
                        'spread': {'type': 'integer'},
                        'real_volume': {'type': 'integer'}
                    }
                }
            }
        },
        400: {
            'description': 'Invalid request parameters.'
        },
        404: {
            'description': 'Failed to get rates data.'
        },
        500: {
            'description': 'Internal server error.'
        }
    }
})
def fetch_data_range_endpoint():
    """
    Fetch Data within a Date Range
    ---
    description: Retrieve historical price data for a given symbol within a specified date range.
    """
    try:
        symbol = request.args.get('symbol')
        timeframe = request.args.get('timeframe', 'M1')
        start_str = request.args.get('start')
        end_str = request.args.get('end')
        
        if not all([symbol, start_str, end_str]):
            return jsonify({"error": "Symbol, start, and end parameters are required"}), 400

        mt5_timeframe = get_timeframe(timeframe)
        
        # Convert string dates to datetime objects
        utc = pytz.UTC
        start_date = utc.localize(datetime.fromisoformat(start_str.replace('Z', '+00:00')))
        end_date = utc.localize(datetime.fromisoformat(end_str.replace('Z', '+00:00')))
        
        rates = mt5.copy_rates_range(symbol, mt5_timeframe, start_date, end_date)
        if rates is None:
            return jsonify({"error": "Failed to get rates data"}), 404
        
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        
        return jsonify(df.to_dict(orient='records'))
    
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error in fetch_data_range: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@data_bp.route('/ticks', methods=['GET'])
def get_ticks_endpoint():
    """Return latest ticks for a symbol"""
    symbol = request.args.get('symbol')
    limit = int(request.args.get('limit', 100))

    if not symbol:
        return jsonify({"error": "symbol parameter is required"}), 400

    ticks = mt5.copy_ticks_from(
        symbol,
        datetime.now(pytz.UTC),
        limit,
        mt5.COPY_TICKS_ALL,
    )

    if ticks is None:
        return jsonify({"error": "Failed to get ticks"}), 404

    df = pd.DataFrame(ticks)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    result = df.to_dict(orient='records')

    if redis_client:
        try:
            redis_client.setex(
                f"ticks:{symbol}:{limit}",
                5,
                json.dumps(result, default=str),
            )
        except Exception:
            pass

    return jsonify(result)


@data_bp.route('/bars/<symbol>/<interval>', methods=['GET'])
def get_bars_endpoint(symbol, interval):
    """Return latest bar data for a symbol and timeframe"""
    limit = int(request.args.get('limit', 100))

    try:
        mt5_timeframe = get_timeframe(interval)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, 0, limit)
    if rates is None:
        return jsonify({"error": "Failed to get rates"}), 404

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    result = df.to_dict(orient='records')

    if redis_client:
        try:
            redis_client.setex(
                f"bars:{symbol}:{interval}:{limit}",
                30,
                json.dumps(result, default=str),
            )
        except Exception:
            pass

    return jsonify(result)
