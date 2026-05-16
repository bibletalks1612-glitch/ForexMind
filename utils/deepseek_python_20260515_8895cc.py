"""
ForexMind - Partial Profit Manager (Standalone)
Closes 50% of position at level1 and remaining 50% at level2.
This file is imported by trailing_stop.py.
"""

import time
import MetaTrader5 as mt5

MAGIC_NUMBER = 234000
CHECK_INTERVAL = 5

PARTIAL_LEVELS = {
    "XAUUSD": (200, 400),
    "EURUSD": (20, 40),
    "GBPUSD": (25, 50),
    "USDJPY": (20, 40),
    "AUDUSD": (20, 40),
    "USDCAD": (20, 40),
}

_hit_levels = {}

def get_pip_value(symbol):
    if "JPY" in symbol:
        return 0.01
    if "XAU" in symbol:
        return 0.1
    return 0.0001

def close_partial(position, percentage, reason):
    vol = round(position.volume * percentage, 2)
    if vol < 0.01:
        return False
    tick = mt5.symbol_info_tick(position.symbol)
    if not tick:
        return False
    if position.type == 0:
        price = tick.bid
        order_type = mt5.ORDER_TYPE_SELL
    else:
        price = tick.ask
        order_type = mt5.ORDER_TYPE_BUY
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "position": position.ticket,
        "symbol": position.symbol,
        "volume": vol,
        "type": order_type,
        "price": price,
        "deviation": 20,
        "magic": MAGIC_NUMBER,
        "comment": f"Partial {int(percentage*100)}% - {reason}",
    }
    result = mt5.order_send(request)
    return result and result.retcode == mt5.TRADE_RETCODE_DONE

def check_and_close_partial(position):
    symbol = position.symbol
    ticket = position.ticket
    base = symbol.replace("_", "").upper()
    levels = PARTIAL_LEVELS.get(base, (15, 30))
    pip = get_pip_value(symbol)
    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        return
    if position.type == 0:
        profit_pips = (tick.bid - position.price_open) / pip
    else:
        profit_pips = (position.price_open - tick.ask) / pip
    if ticket not in _hit_levels:
        _hit_levels[ticket] = 0
    if _hit_levels[ticket] < 1 and profit_pips >= levels[0]:
        if close_partial(position, 0.5, f"Level1 ({levels[0]} pips)"):
            _hit_levels[ticket] = 1
    elif _hit_levels[ticket] == 1 and profit_pips >= levels[1]:
        close_partial(position, 0.5, f"Level2 ({levels[1]} pips)")
        _hit_levels[ticket] = 2

def check_all_positions():
    if not mt5.initialize():
        return
    positions = mt5.positions_get()
    if not positions:
        return
    for pos in positions:
        if pos.magic == MAGIC_NUMBER:
            check_and_close_partial(pos)

def run_partial_monitor():
    print("Partial Profit Monitor Started")
    while True:
        check_all_positions()
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    run_partial_monitor()