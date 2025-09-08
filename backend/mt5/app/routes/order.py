from flask import Blueprint, jsonify, request
import MetaTrader5 as mt5
import logging
from flasgger import swag_from


def _normalize_order_type(t):
    """Accept 'BUY'/'SELL' (case-insensitive) or MT5 numeric constant.

    Returns mt5.ORDER_TYPE_BUY or mt5.ORDER_TYPE_SELL, or None if invalid.
    """
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


def _normalize_filling(val):
    """Accept string names or numeric constants for type_filling."""
    try:
        if isinstance(val, int):
            return val
        if isinstance(val, str):
            s = val.strip().upper()
            mapping = {
                'ORDER_FILLING_IOC': mt5.ORDER_FILLING_IOC,
                'ORDER_FILLING_FOK': mt5.ORDER_FILLING_FOK,
                'ORDER_FILLING_RETURN': mt5.ORDER_FILLING_RETURN,
            }
            return mapping.get(s, mt5.ORDER_FILLING_IOC)
    except Exception:
        pass
    return mt5.ORDER_FILLING_IOC

order_bp = Blueprint('order', __name__)
logger = logging.getLogger(__name__)

@order_bp.route('/order', methods=['POST'])
@order_bp.route('/send_market_order', methods=['POST'])
@swag_from({
    'tags': ['Order'],
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'symbol': {'type': 'string'},
                    'volume': {'type': 'number'},
                    'type': {'type': 'string', 'enum': ['BUY', 'SELL']},
                    'deviation': {'type': 'integer', 'default': 20},
                    'magic': {'type': 'integer', 'default': 0},
                    'comment': {'type': 'string', 'default': ''},
                    'type_filling': {'type': 'string', 'enum': ['ORDER_FILLING_IOC', 'ORDER_FILLING_FOK', 'ORDER_FILLING_RETURN']},
                    'sl': {'type': 'number'},
                    'tp': {'type': 'number'}
                },
                'required': ['symbol', 'volume', 'type']
            }
        }
    ],
    'responses': {
        200: {
            'description': 'Order executed successfully.',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'},
                    'result': {
                        'type': 'object',
                        'properties': {
                            'retcode': {'type': 'integer'},
                            'order': {'type': 'integer'},
                            'magic': {'type': 'integer'},
                            'price': {'type': 'number'},
                            'symbol': {'type': 'string'},
                            # Add other relevant fields as needed
                        }
                    }
                }
            }
        },
        400: {
            'description': 'Bad request or order failed.'
        },
        500: {
            'description': 'Internal server error.'
        }
    }
})
def send_market_order_endpoint():
    """
    Send Market Order
    ---
    description: Execute a market order for a specified symbol with optional parameters.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Order data is required"}), 400

        required_fields = ['symbol', 'volume', 'type']
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400

        # Normalize inputs
        order_type = _normalize_order_type(data.get('type') or data.get('order_type'))
        if order_type is None:
            return jsonify({"error": "Invalid order type; use BUY/SELL"}), 400
        type_filling = _normalize_filling(data.get('type_filling', mt5.ORDER_FILLING_IOC))

        # Prepare the order request
        request_data = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": data['symbol'],
            "volume": float(data['volume']),
            "type": order_type,
            "deviation": int(data.get('deviation', 20)),
            "magic": int(data.get('magic', 0)),
            "comment": data.get('comment', ''),
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": int(type_filling),
        }

        # Get current price
        tick = mt5.symbol_info_tick(data['symbol'])
        if tick is None:
            return jsonify({"error": "Failed to get symbol price"}), 400

        # Set price based on order type
        if order_type == mt5.ORDER_TYPE_BUY:
            request_data["price"] = tick.ask
        elif order_type == mt5.ORDER_TYPE_SELL:
            request_data["price"] = tick.bid
        else:
            return jsonify({"error": "Invalid order type"}), 400

        # Add optional SL/TP if provided
        if 'sl' in data:
            request_data["sl"] = data['sl']
        if 'tp' in data:
            request_data["tp"] = data['tp']

        # Send order
        result = mt5.order_send(request_data)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            error_code, error_str = mt5.last_error()
            
            return jsonify({
                "error": f"Order failed: {result.comment}",
                "mt5_error": error_str,
                "result": result._asdict()
            }), 400

        # Back-compat shape used by Django helper
        return jsonify({
            "success": True,
            "message": "Order executed successfully",
            "order_result": result._asdict(),
            "result": result._asdict(),
        })
    
    except Exception as e:
        logger.error(f"Error in send_market_order: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@order_bp.route('/modify_sl_tp', methods=['POST'])
@swag_from({
    'tags': ['Order'],
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'ticket': {'type': 'integer'},
                    'symbol': {'type': 'string'},
                    'sl': {'type': 'number'},
                    'tp': {'type': 'number'}
                },
                'required': ['ticket', 'symbol']
            }
        }
    ],
    'responses': {
        200: {
            'description': 'SL/TP modified successfully.',
            'schema': {'type': 'object'}
        },
        400: {'description': 'Bad request or modification failed.'},
        500: {'description': 'Internal server error.'}
    }
})
def modify_sl_tp_endpoint():
    """
    Modify SL/TP of an open position via TRADE_ACTION_SLTP.
    """
    try:
        data = request.get_json() or {}
        ticket = data.get('ticket')
        symbol = data.get('symbol')
        sl = data.get('sl')
        tp = data.get('tp')
        if ticket is None or not symbol:
            return jsonify({"error": "ticket and symbol required"}), 400

        req = {
            'action': mt5.TRADE_ACTION_SLTP,
            'position': int(ticket),
            'symbol': symbol,
            'deviation': 20,
            'type_time': mt5.ORDER_TIME_GTC,
            'type_filling': mt5.ORDER_FILLING_IOC,
        }
        if sl is not None:
            req['sl'] = float(sl)
        if tp is not None:
            req['tp'] = float(tp)

        result = mt5.order_send(req)
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            return jsonify({"ok": True, "result": result._asdict()})
        # On failure, include MT5 error details
        err = mt5.last_error()
        return jsonify({
            "error": "modify_failed",
            "retcode": getattr(result, 'retcode', None),
            "result": getattr(result, '_asdict', lambda: {})(),
            "mt5_error": err
        }), 400
    except Exception as e:
        logger.error(f"Error in modify_sl_tp: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@order_bp.route('/partial_close', methods=['POST'])
@swag_from({
    'tags': ['Order'],
    'parameters': [{
        'name': 'body', 'in': 'body', 'required': True,
        'schema': {
            'type': 'object',
            'properties': {
                'ticket': {'type': 'integer'},
                'symbol': {'type': 'string'},
                'fraction': {'type': 'number', 'minimum': 0.01, 'maximum': 0.99}
            },
            'required': ['ticket', 'symbol', 'fraction']
        }
    }]
})
def partial_close_endpoint():
    try:
        data = request.get_json() or {}
        ticket = int(data.get('ticket'))
        symbol = data.get('symbol')
        fraction = float(data.get('fraction'))
        if not (0 < fraction < 1):
            return jsonify({'error': 'fraction must be between 0 and 1'}), 400
        # Find position
        pos = None
        positions = mt5.positions_get()
        if positions:
            for p in positions:
                if int(p.ticket) == ticket:
                    pos = p
                    break
        if pos is None:
            return jsonify({'error': 'position not found'}), 404
        vol_to_close = round(float(pos.volume) * fraction, 2)
        if vol_to_close <= 0:
            return jsonify({'error': 'computed close volume <= 0'}), 400
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return jsonify({'error': 'no tick'}), 400
        opposite = mt5.ORDER_TYPE_SELL if int(pos.type) == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        price = tick.bid if opposite == mt5.ORDER_TYPE_SELL else tick.ask
        req = {
            'action': mt5.TRADE_ACTION_DEAL,
            'position': ticket,
            'symbol': symbol,
            'volume': vol_to_close,
            'type': opposite,
            'price': price,
            'deviation': 20,
            'type_time': mt5.ORDER_TIME_GTC,
            'type_filling': mt5.ORDER_FILLING_IOC,
        }
        result = mt5.order_send(req)
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            return jsonify({'ok': True, 'success': True, 'result': result._asdict()})
        err = mt5.last_error()
        return jsonify({'error': 'partial_close_failed', 'retcode': getattr(result, 'retcode', None), 'mt5_error': err}), 400
    except Exception as e:
        logger.error(f"Error in partial_close: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@order_bp.route('/partial_close_v2', methods=['POST'])
def partial_close_v2_endpoint():
    """Enhanced partial close: accept either fraction (0..1) or explicit volume.

    If both provided, 'volume' takes precedence. 'symbol' is optional and inferred from the position.
    """
    try:
        data = request.get_json() or {}
        ticket = int(data.get('ticket'))
        fraction = data.get('fraction')
        volume_req = data.get('volume')
        if ticket is None:
            return jsonify({'error': 'ticket required'}), 400
        # Locate position by ticket
        pos = None
        positions = mt5.positions_get() or []
        for p in positions:
            if int(p.ticket) == int(ticket):
                pos = p
                break
        if pos is None:
            return jsonify({'error': 'position not found'}), 404
        symbol = str(pos.symbol)
        # Determine volume to close
        if volume_req is not None:
            vol_to_close = float(volume_req)
        else:
            if fraction is None:
                return jsonify({'error': 'fraction or volume required'}), 400
            f = float(fraction)
            if not (0 < f < 1):
                return jsonify({'error': 'fraction must be (0,1)'}), 400
            vol_to_close = float(pos.volume) * f
        # Respect volume step and min
        sinfo = mt5.symbol_info(symbol)
        vol_min = getattr(sinfo, 'volume_min', 0.01) if sinfo else 0.01
        vol_step = getattr(sinfo, 'volume_step', 0.01) if sinfo else 0.01
        # Round down to nearest step
        steps = max(1, int(vol_to_close / vol_step + 1e-9))
        vol_to_close = round(steps * vol_step, 2)
        if vol_to_close < vol_min:
            return jsonify({'error': 'computed close volume below minimum', 'min': vol_min}), 400
        if vol_to_close > float(pos.volume):
            vol_to_close = float(pos.volume)
        # Build close request
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return jsonify({'error': 'no tick'}), 400
        opposite = mt5.ORDER_TYPE_SELL if int(pos.type) == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        price = tick.bid if opposite == mt5.ORDER_TYPE_SELL else tick.ask
        req = {
            'action': mt5.TRADE_ACTION_DEAL,
            'position': int(ticket),
            'symbol': symbol,
            'volume': float(vol_to_close),
            'type': int(opposite),
            'price': float(price),
            'deviation': 20,
            'type_time': mt5.ORDER_TIME_GTC,
            'type_filling': mt5.ORDER_FILLING_IOC,
        }
        result = mt5.order_send(req)
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            return jsonify({'ok': True, 'success': True, 'result': result._asdict()})
        err = mt5.last_error()
        return jsonify({'error': 'partial_close_failed', 'retcode': getattr(result, 'retcode', None), 'mt5_error': err}), 400
    except Exception as e:
        logger.error(f"Error in partial_close_v2: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@order_bp.route('/scale_position', methods=['POST'])
def scale_position_endpoint():
    """Increase position size by submitting an additional market order in the same direction.

    Body: { ticket: int, additional_volume: float }
    """
    try:
        data = request.get_json() or {}
        ticket = int(data.get('ticket'))
        add_vol = float(data.get('additional_volume'))
        if add_vol <= 0:
            return jsonify({'error': 'additional_volume must be > 0'}), 400
        pos = None
        positions = mt5.positions_get() or []
        for p in positions:
            if int(p.ticket) == int(ticket):
                pos = p
                break
        if pos is None:
            return jsonify({'error': 'position not found'}), 404
        order_type = mt5.ORDER_TYPE_BUY if int(pos.type) == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_SELL
        tick = mt5.symbol_info_tick(pos.symbol)
        if tick is None:
            return jsonify({'error': 'no tick'}), 400
        price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid
        req = {
            'action': mt5.TRADE_ACTION_DEAL,
            'symbol': str(pos.symbol),
            'volume': float(add_vol),
            'type': int(order_type),
            'price': float(price),
            'deviation': 20,
            'type_time': mt5.ORDER_TIME_GTC,
            'type_filling': mt5.ORDER_FILLING_IOC,
        }
        result = mt5.order_send(req)
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            return jsonify({'ok': True, 'success': True, 'result': result._asdict()})
        err = mt5.last_error()
        return jsonify({'error': 'scale_failed', 'retcode': getattr(result, 'retcode', None), 'mt5_error': err}), 400
    except Exception as e:
        logger.error(f"Error in scale_position: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@order_bp.route('/hedge', methods=['POST'])
def hedge_endpoint():
    """Open an opposite-direction position to hedge an existing one.

    Body: either { ticket: int, volume: float } or { symbol: str, volume: float, type: 'BUY'|'SELL' }.
    If ticket is provided, side is inferred as the opposite of the ticket's position.
    """
    try:
        data = request.get_json() or {}
        ticket = data.get('ticket')
        symbol = data.get('symbol')
        volume = float(data.get('volume')) if data.get('volume') is not None else None
        if volume is None or volume <= 0:
            return jsonify({'error': 'volume must be > 0'}), 400
        if ticket is not None:
            # Hedge specific position
            pos = None
            positions = mt5.positions_get() or []
            for p in positions:
                if int(p.ticket) == int(ticket):
                    pos = p
                    break
            if pos is None:
                return jsonify({'error': 'position not found'}), 404
            symbol = str(pos.symbol)
            side = mt5.ORDER_TYPE_SELL if int(pos.type) == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        else:
            if not symbol:
                return jsonify({'error': 'symbol or ticket required'}), 400
            # Use provided type but it should be the hedge direction the caller desires
            side = _normalize_order_type(data.get('type'))
            if side is None:
                return jsonify({'error': 'type BUY/SELL required'}), 400
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return jsonify({'error': 'no tick'}), 400
        price = tick.bid if side == mt5.ORDER_TYPE_SELL else tick.ask
        req = {
            'action': mt5.TRADE_ACTION_DEAL,
            'symbol': str(symbol),
            'volume': float(volume),
            'type': int(side),
            'price': float(price),
            'deviation': 20,
            'type_time': mt5.ORDER_TIME_GTC,
            'type_filling': mt5.ORDER_FILLING_IOC,
        }
        result = mt5.order_send(req)
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            return jsonify({'ok': True, 'success': True, 'result': result._asdict()})
        err = mt5.last_error()
        return jsonify({'error': 'hedge_failed', 'retcode': getattr(result, 'retcode', None), 'mt5_error': err}), 400
    except Exception as e:
        logger.error(f"Error in hedge: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500
