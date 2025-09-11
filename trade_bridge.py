try:
    import MetaTrader5 as mt5  # type: ignore
except Exception as exc:  # pragma: no cover - runtime import guard
    mt5 = None
    _import_error = exc


def _ensure_connected():
    if mt5 is None:
        raise RuntimeError(f"MetaTrader5 module not available: {_import_error}")
    if not mt5.initialize():
        raise RuntimeError(f"MT5 init failed: {mt5.last_error()}")


def _symbol_info_tick(symbol):
    info = mt5.symbol_info(symbol)
    if info is None or not info.visible:
        if not mt5.symbol_select(symbol, True):
            raise RuntimeError(f"Cannot select symbol {symbol}")
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise RuntimeError(f"No tick for {symbol}")
    return info, tick


def _assert_ok(result):
    if result is None:
        raise RuntimeError(f"order_send returned None: {mt5.last_error()}")
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        raise RuntimeError(f"Broker rejected ({result.retcode}): {result.comment}")
    return result


def open_position(
    symbol,
    side,
    volume,
    type_="market",
    price=None,
    sl=None,
    tp=None,
    deviation=10,
    magic=777,
):
    _ensure_connected()
    info, tick = _symbol_info_tick(symbol)

    if type_ == "market":
        order_type = mt5.ORDER_TYPE_BUY if side == "buy" else mt5.ORDER_TYPE_SELL
        price_used = tick.ask if side == "buy" else tick.bid
    elif type_ == "limit":
        order_type = mt5.ORDER_TYPE_BUY_LIMIT if side == "buy" else mt5.ORDER_TYPE_SELL_LIMIT
        price_used = float(price)
    elif type_ == "stop":
        order_type = mt5.ORDER_TYPE_BUY_STOP if side == "buy" else mt5.ORDER_TYPE_SELL_STOP
        price_used = float(price)
    else:
        raise ValueError("type_ must be market|limit|stop")

    request = {
        "action": mt5.TRADE_ACTION_DEAL if type_ == "market" else mt5.TRADE_ACTION_PENDING,
        "symbol": symbol,
        "volume": float(volume),
        "type": order_type,
        "price": price_used,
        "sl": float(sl) if sl else 0.0,
        "tp": float(tp) if tp else 0.0,
        "deviation": int(deviation),
        "magic": int(magic),
        "comment": "open_v1",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC if type_ == "market" else mt5.ORDER_FILLING_RETURN,
    }

    result = mt5.order_send(request)
    return _assert_ok(result)


def close_position(ticket, volume=None, deviation=10, magic=777):
    _ensure_connected()
    pos = next((p for p in mt5.positions_get() if p.ticket == ticket), None)
    if pos is None:
        raise ValueError(f"Position {ticket} not found")

    vol_to_close = float(volume) if volume else float(pos.volume)
    # Use opposite side to close the position
    side = mt5.ORDER_TYPE_SELL if pos.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
    # Need current tick price for DEAL
    _, tick = _symbol_info_tick(pos.symbol)
    price = tick.bid if side == mt5.ORDER_TYPE_SELL else tick.ask

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "position": ticket,
        "symbol": pos.symbol,
        "volume": vol_to_close,
        "type": side,
        "price": float(price),
        "deviation": int(deviation),
        "magic": int(magic),
        "comment": "close_v1",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    return _assert_ok(result)


def modify_sl_tp(ticket, sl=None, tp=None):
    _ensure_connected()
    pos = next((p for p in mt5.positions_get() if p.ticket == ticket), None)
    if pos is None:
        raise ValueError(f"Position {ticket} not found")

    new_sl = float(sl) if sl else pos.sl
    new_tp = float(tp) if tp else pos.tp

    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "position": ticket,
        "symbol": pos.symbol,
        "sl": new_sl if new_sl else 0.0,
        "tp": new_tp if new_tp else 0.0,
        "comment": "modify_v1",
    }
    result = mt5.order_send(request)
    return _assert_ok(result)
