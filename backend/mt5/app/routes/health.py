from flask import Blueprint, Response, jsonify
import MetaTrader5 as mt5
from flasgger import swag_from
from prometheus_client import CONTENT_TYPE_LATEST, Gauge, Histogram, generate_latest
import time
import logging

health_bp = Blueprint('health', __name__)
logger = logging.getLogger(__name__)

# Metrics
mt5_connection_gauge = Gauge(
    "mt5_connection_status", "1 if MetaTrader5 module is available"
)
mt5_alive_gauge = Gauge(
    "mt5_terminal_info_result", "1 if mt5.terminal_info() succeeds"
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
                    'mt5_alive': {'type': 'boolean'}
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
    mt5_ok = False
    if mt5 is not None:
        try:
            mt5_ok = mt5.terminal_info() is not None
        except Exception:
            logger.exception("mt5.terminal_info() failed")
            mt5_ok = False
    mt5_connection_gauge.set(1 if mt5 is not None else 0)
    mt5_alive_gauge.set(1 if mt5_ok else 0)
    latency = time.time() - start
    health_latency_histogram.observe(latency)
    return jsonify({
        "status": "healthy",
        "mt5_connected": mt5 is not None,
        "mt5_alive": bool(mt5_ok),
    }), 200


@health_bp.route('/metrics')
def metrics():
    """Expose Prometheus metrics"""
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)
