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
    """Initialize MT5 and ensure login if MT5_LOGIN/MT5_PASSWORD/MT5_SERVER are provided."""
    try:
        # initialize() returns False if already initialized in some environments; that's fine
        mt5.initialize()
    except Exception:
        pass
    try:
        login_env = os.getenv("MT5_LOGIN")
        password_env = os.getenv("MT5_PASSWORD")
        server_env = os.getenv("MT5_SERVER")
        if login_env and password_env and server_env:
            ai = None
            try:
                ai = mt5.account_info()
            except Exception:
                ai = None
            need_login = ai is None
            try:
                if ai and str(getattr(ai, "login", "")) != str(login_env):
                    need_login = True
            except Exception:
                need_login = True
            if need_login:
                try:
                    mt5.login(login=int(login_env), password=password_env, server=server_env)
                except Exception:
                    # Non-fatal; endpoints will surface failures
                    pass
    except Exception:
        # Non-fatal guard
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

# ---- Fallback order/position endpoints (registered only if missing) ----
def _route_missing(rule: str) -> bool:
    try:
        for r in app.url_map.iter_rules():
            if r.rule == rule:
                return False
    except Exception:
        pass
    return True

def _normalize_order_type(t):
    try:
        if isinstance(t, int):
            if t in (mt5.ORDER_TYPE_BUY, mt5.ORDER_TYPE_SELL):
                return t
            return None
        if isinstance(t, str):
            s = t.strip().upper()
            if s == 'BUY':
                return mt5.ORDER_TYPE_BUY
            if s == 'SELL':
                return mt5.ORDER_TYPE_SELL
    except Exception:
        return None
    return None

def _json():
    try:
        return request.get_json() or {}
    except Exception:
        return {}

def _send_deal(symbol: str, volume: float, order_type: int):
    _ensure_mt5()
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return jsonify({'error': 'no tick'}), 400
    price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid
    req = {
        'action': mt5.TRADE_ACTION_DEAL,
        'symbol': str(symbol),
        'volume': float(volume),
        'type': int(order_type),
        'price': float(price),
        'deviation': 20,
        'type_time': mt5.ORDER_TIME_GTC,
        'type_filling': mt5.ORDER_FILLING_IOC,
    }
    res = mt5.order_send(req)
    if res and getattr(res, 'retcode', None) == mt5.TRADE_RETCODE_DONE:
        return jsonify({'ok': True, 'success': True, 'result': res._asdict()})
    return jsonify({'error': 'order_failed', 'retcode': getattr(res, 'retcode', None)}), 400

def _find_position(ticket: int):
    _ensure_mt5()
    for p in (mt5.positions_get() or []):
        try:
            if int(p.ticket) == int(ticket):
                return p
        except Exception:
            continue
    return None

def compat_send_market_order():
    d = _json()
    symbol = d.get('symbol')
    volume = d.get('volume')
    t = _normalize_order_type(d.get('type') or d.get('order_type'))
    try:
        vol = float(volume)
    except Exception:
        return jsonify({'error': 'volume required'}), 400
    if not symbol or t is None:
        return jsonify({'error': 'symbol and type required'}), 400
    return _send_deal(symbol, vol, t)

def compat_partial_close_v2():
    d = _json()
    try:
        ticket = int(d.get('ticket'))
    except Exception:
        return jsonify({'error': 'ticket required'}), 400
    pos = _find_position(ticket)
    if pos is None:
        return jsonify({'error': 'position not found'}), 404
    vol_req = d.get('volume')
    fraction = d.get('fraction')
    if vol_req is None and fraction is None:
        return jsonify({'error': 'fraction or volume required'}), 400
    try:
        vol_to_close = float(vol_req) if vol_req is not None else float(pos.volume) * float(fraction)
    except Exception:
        return jsonify({'error': 'invalid volume/fraction'}), 400
    # Respect min/step if available
    sinfo = mt5.symbol_info(pos.symbol)
    vol_min = getattr(sinfo, 'volume_min', 0.01) if sinfo else 0.01
    vol_step = getattr(sinfo, 'volume_step', 0.01) if sinfo else 0.01
    steps = max(1, int(vol_to_close / vol_step + 1e-9))
    vol_to_close = steps * vol_step
    if vol_to_close < vol_min:
        return jsonify({'error': 'computed close volume below minimum', 'min': vol_min}), 400
    if vol_to_close > float(pos.volume):
        vol_to_close = float(pos.volume)
    opposite = mt5.ORDER_TYPE_SELL if int(pos.type) == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
    return _send_deal(pos.symbol, float(vol_to_close), opposite)

def compat_partial_close():
    d = _json()
    try:
        ticket = int(d.get('ticket'))
        symbol = str(d.get('symbol') or '')
        fraction = float(d.get('fraction'))
    except Exception:
        return jsonify({'error': 'ticket, symbol, fraction required'}), 400
    if not (0 < fraction < 1):
        return jsonify({'error': 'fraction must be (0,1)'}), 400
    pos = _find_position(ticket)
    if pos is None:
        return jsonify({'error': 'position not found'}), 404
    opposite = mt5.ORDER_TYPE_SELL if int(pos.type) == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
    vol_to_close = float(pos.volume) * fraction
    return _send_deal(symbol or pos.symbol, float(vol_to_close), opposite)

def compat_close_position():
    d = _json()
    try:
        p = d.get('position') or {}
        ticket = int(p.get('ticket'))
        symbol = str(p.get('symbol'))
        vol = float(p.get('volume'))
        ptype = int(p.get('type'))
    except Exception:
        return jsonify({'error': 'position payload invalid'}), 400
    opposite = mt5.ORDER_TYPE_SELL if ptype == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
    return _send_deal(symbol, vol, opposite)

# Conditionally register fallbacks if routes are missing
if _route_missing('/send_market_order'):
    app.add_url_rule('/send_market_order', view_func=compat_send_market_order, methods=['POST'])
if _route_missing('/order'):
    app.add_url_rule('/order', view_func=compat_send_market_order, methods=['POST'])
if _route_missing('/partial_close_v2'):
    app.add_url_rule('/partial_close_v2', view_func=compat_partial_close_v2, methods=['POST'])
if _route_missing('/partial_close'):
    app.add_url_rule('/partial_close', view_func=compat_partial_close, methods=['POST'])
if _route_missing('/close_position'):
    app.add_url_rule('/close_position', view_func=compat_close_position, methods=['POST'])
# ---- end fallback endpoints ----

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
