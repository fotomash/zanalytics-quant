import logging
import os
from flask import Flask
from dotenv import load_dotenv
import MetaTrader5 as mt5
from flasgger import Swagger
from werkzeug.middleware.proxy_fix import ProxyFix
try:
    from swagger import swagger_config
except Exception:
    swagger_config = None

# Import routes
from routes.health import health_bp
from routes.symbol import symbol_bp
from routes.data import data_bp
from routes.position import position_bp
from routes.order import order_bp
from routes.history import history_bp
from routes.error import error_bp
from flask import jsonify, request

load_dotenv()
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['PREFERRED_URL_SCHEME'] = 'https'

# ---- Compatibility endpoints (direct MT5 access) ----
def _ensure_mt5():
    """Initialize MT5 once if needed; safe no-op if already initialized."""
    try:
        # initialize() returns False if already initialized in some environments; that's fine
        mt5.initialize()
    except Exception:
        pass

@app.get("/account_info")
def account_info_alias():
    _ensure_mt5()
    info = mt5.account_info()
    if not info:
        return jsonify({"error": "mt5.account_info() unavailable"}), 503
    return jsonify(info._asdict())

@app.get("/symbol_info_tick/<symbol>")
def symbol_info_tick_alias(symbol: str):
    _ensure_mt5()
    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        return jsonify({"error": f"No tick for {symbol}"}), 404
    return jsonify(tick._asdict())

@app.get("/positions_get")
def positions_get_alias():
    _ensure_mt5()
    positions = mt5.positions_get()
    if not positions:
        return jsonify([])
    return jsonify([p._asdict() for p in positions])
# ---- end compatibility endpoints ----

try:
    if swagger_config:
        swagger = Swagger(app, config=swagger_config)
except Exception:
    # Do not block API if Swagger UI fails
    pass

# Register blueprints
app.register_blueprint(health_bp)
app.register_blueprint(symbol_bp)
app.register_blueprint(data_bp)
app.register_blueprint(position_bp)
app.register_blueprint(order_bp)
app.register_blueprint(history_bp)
app.register_blueprint(error_bp)

app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

if __name__ == '__main__':
    port = int(os.environ.get('MT5_API_PORT', '5001'))
    try:
        if not mt5.initialize():
            logger.warning("MT5 initialize() returned False; API will still start and attempt lazy init on requests.")
    except Exception as e:
        logger.warning("MT5 initialize() raised %s; API will still start.", e)
    print(f"[MT5-API] Starting Flask on 0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port)
