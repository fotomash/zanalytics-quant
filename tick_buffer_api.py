from flask import Flask, request, jsonify
import random
from datetime import datetime

app = Flask(__name__)


def generate_mock_ticks(symbol, base_price):
    ticks = []
    current_time = datetime.now()
    for _ in range(5):
        price_change = random.uniform(-0.5, 0.5) / 100 * base_price
        price = base_price + price_change
        timestamp = current_time.strftime("%H:%M:%S")
        ticks.append({"timestamp": timestamp, "price": round(price, 2)})
        current_time = current_time.replace(second=current_time.second + 5)
        base_price = price
    return ticks


@app.get('/get_tick_buffer')
def get_tick_buffer():
    symbol = request.args.get('symbol', '').upper()
    if not symbol:
        return jsonify({"error": "Symbol parameter required"}), 400
    base_prices = {'BTC': 105000, 'ETH': 3500, 'SOL': 180, 'ADA': 0.45, 'DOT': 8.5}
    if symbol not in base_prices:
        return jsonify({"error": f"Symbol {symbol} not supported"}), 400
    ticks = generate_mock_ticks(symbol, base_prices[symbol])
    return jsonify({"symbol": symbol, "ticks": ticks, "source": "Mock Data API", "timestamp": datetime.now().isoformat()})


@app.get('/get_crypto_price')
def get_crypto_price():
    symbol = request.args.get('symbol', '').upper()
    if not symbol:
        return jsonify({"error": "Symbol parameter required"}), 400
    base_prices = {'BTC': 105000, 'ETH': 3500, 'SOL': 180, 'ADA': 0.45, 'DOT': 8.5}
    if symbol not in base_prices:
        return jsonify({"error": f"Symbol {symbol} not supported"}), 400
    base_price = base_prices[symbol]
    current_price = base_price + random.uniform(-2, 2) / 100 * base_price
    change_24h = random.uniform(-5, 5)
    return jsonify({
        "symbol": symbol,
        "price": round(current_price, 2),
        "change_24h": round(change_24h, 2),
        "timestamp": datetime.now().isoformat(),
        "source": "Mock API"
    })


@app.get('/openapi.json')
def openapi_spec():
    from flask import send_file
    return send_file('openapi.json', mimetype='application/json')


if __name__ == '__main__':
    app.run(debug=True, port=5000)
