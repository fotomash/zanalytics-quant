from flask import Blueprint, jsonify, request
import MetaTrader5 as mt5
import logging
from flasgger import swag_from

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

        # Prepare the order request
        request_data = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": data['symbol'],
            "volume": float(data['volume']),
            "type": data['type'],
            "deviation": data.get('deviation', 20),
            "magic": data.get('magic', 0),
            "comment": data.get('comment', ''),
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": data.get('type_filling', mt5.ORDER_FILLING_IOC),
        }

        # Get current price
        tick = mt5.symbol_info_tick(data['symbol'])
        if tick is None:
            return jsonify({"error": "Failed to get symbol price"}), 400

        # Set price based on order type
        if data['type'] == mt5.ORDER_TYPE_BUY:
            request_data["price"] = tick.ask
        elif data['type'] == mt5.ORDER_TYPE_SELL:
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

        return jsonify({
            "message": "Order executed successfully",
            "result": result._asdict()
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
