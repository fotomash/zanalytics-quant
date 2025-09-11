from flask import Blueprint, Response, jsonify
import MetaTrader5 as mt5
from flasgger import swag_from
from prometheus_client import CONTENT_TYPE_LATEST, Gauge, Histogram, generate_latest
import time

health_bp = Blueprint('health', __name__)

# Metrics
mt5_connection_gauge = Gauge(
    "mt5_connection_status", "1 if MetaTrader5 module is available"
)
mt5_initialized_gauge = Gauge(
    "mt5_initialization_result", "1 if mt5.initialize() succeeds"
)
health_latency_histogram = Histogram(
    "mt5_health_request_latency_seconds", "Latency for /health endpoint"
)

@health_bp.route('/health')
@swag_from({
    'tags': ['Health'],
    'responses': {
        200: {
            'description': 'Health check successful',
            'schema': {
                'type': 'object',
                'properties': {
                    'status': {'type': 'string'},
                    'mt5_connected': {'type': 'boolean'},
                    'mt5_initialized': {'type': 'boolean'}
                }
            }
        }
    }
})
def health_check():
    """
    Health Check Endpoint
    ---
    description: Check the health status of the application and MT5 connection.
    responses:
      200:
        description: Health check successful
    """
    start = time.time()
    initialized = mt5.initialize() if mt5 is not None else False
    mt5_connection_gauge.set(1 if mt5 is not None else 0)
    mt5_initialized_gauge.set(1 if initialized else 0)
    latency = time.time() - start
    health_latency_histogram.observe(latency)
    return jsonify({
        "status": "healthy",
        "mt5_connected": mt5 is not None,
        "mt5_initialized": bool(initialized),
    }), 200


@health_bp.route('/metrics')
def metrics():
    """Expose Prometheus metrics"""
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)
