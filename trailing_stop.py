"""
ForexMind - Trailing Stop + Partial Profit Monitor (FINAL)
Features:
  ✅ XAUUSD pip size: 0.1 (correct for gold ~4600)
  ✅ Gold trail: 150 pips, breakeven: 80 pips
  ✅ Partial profit: 50% close at 200 pips (gold) / 20 pips (forex)
  ✅ Second partial: remaining 50% at 400 pips (gold) / 40 pips (forex)
  ✅ Telegram alert for each partial close
  ✅ Day-end close at 20:00 UTC
  ✅ Cleans up _partial_hit when position is fully closed
  ❌ NOT using 300 pip initial SL (DeepSeek suggestion rejected — too wide)
     Our mt5_executor.py already sets 150 pip initial SL for gold
"""

import time
import os
from datetime import datetime, timezone

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False

MAGIC_NUMBER   = 234000
CHECK_INTERVAL = 10

# Pair config: (pip_size, trail_pips, breakeven_pips)
PAIR_CONFIG = {
    "XAUUSD":  (0.1,     150, 80),   # Gold: wide trail for volatility
    "EURUSD":  (0.0001,   30, 20),
    "GBPUSD":  (0.0001,   35, 25),
    "USDJPY":  (0.01,     30, 20),
    "USDCHF":  (0.0001,   30, 20),
    "AUDUSD":  (0.0001,   30, 20),
    "NZDUSD":  (0.0001,   30, 20),
    "USDCAD":  (0.0001,   30, 20),
    "EURGBP":  (0.0001,   30, 20),
    "EURJPY":  (0.01,     30, 20),
    "GBPJPY":  (0.01,     35, 25),
}

# Partial profit levels (pips): close 50% at level1, 50% of remainder at level2
PARTIAL_LEVELS = {
    "XAUUSD": (200, 400),   # gold: 200 pips → close 50%, 400 pips → close 50% more
    "default": (20, 40),    # forex: 20 pips → close 50%, 40 pips → close 50% more
}

MIN_PROFIT_LOCK = 5   # pips to lock after breakeven

_partial_hit = {}   # ticket → level already triggered (0, 1, or 2)


def get_config(symbol):
    sym = symbol.upper().replace("_", "")
    if sym in PAIR_CONFIG:
        return PAIR_CONFIG[sym]
    if "JPY" in sym:
        return (0.01, 30, 20)
    if "XAU" in sym or "GOLD" in sym:
        return (0.1, 150, 80)
    return (0.0001, 30, 20)


def get_partial_levels(symbol):
    sym = symbol.upper().replace("_", "")
    return PARTIAL_LEVELS.get(sym, PARTIAL_LEVELS["default"])


def connect_mt5():
    if not MT5_AVAILABLE:
        return False
    if not mt5.initialize():
        print(f"[Trail] MT5 init failed: {mt5.last_error()}")
        return False
    print("[Trail] MT5 connected ✓")
    return True


def get_forexmind_positions():
    if not MT5_AVAILABLE:
        return []
    positions = mt5.positions_get()
    if not positions:
        return []
    return [p for p in positions if p.magic == MAGIC_NUMBER]


def send_telegram(message):
    """Send Telegram notification."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        import requests
        token   = os.getenv("TELEGRAM_BOT_TOKEN", "")
        chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        if not token or not chat_id:
            return
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"},
            timeout=10
        )
    except Exception:
        pass


def close_partial_position(position, percentage=0.5, reason=""):
    """Close a percentage of a position. Returns True on success."""
    symbol = position.symbol
    ticket = position.ticket
    volume = round(position.volume * percentage, 2)
    if volume < 0.01:
        volume = 0.01

    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        return False

    price      = tick.bid if position.type == 0 else tick.ask
    order_type = mt5.ORDER_TYPE_SELL if position.type == 0 else mt5.ORDER_TYPE_BUY

    request = {
        "action":    mt5.TRADE_ACTION_DEAL,
        "position":  ticket,
        "symbol":    symbol,
        "volume":    volume,
        "type":      order_type,
        "price":     price,
        "deviation": 20,
        "magic":     MAGIC_NUMBER,
        "comment":   f"Partial {int(percentage*100)}% - {reason}",
    }
    result = mt5.order_send(request)
    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
        direction = "BUY" if position.type == 0 else "SELL"
        print(f"  [Trail] 💰 Partial close {int(percentage*100)}% of "
              f"{symbol} {direction} #{ticket} — {reason}")
        send_telegram(
            f"💰 <b>Partial Profit Taken</b>\n"
            f"{symbol} {direction} #{ticket}\n"
            f"Closed {int(percentage*100)}% at {reason}\n"
            f"Remaining: {round(position.volume - volume, 2)} lots"
        )
        return True
    else:
        retcode = result.retcode if result else "None"
        print(f"  [Trail] ❌ Partial close failed {symbol} #{ticket}: {retcode}")
        return False


def check_partial_profit(position):
    """
    Close 50% at level1 pips profit, then 50% of remainder at level2.
    Prevents duplicate triggers using _partial_hit dict.
    """
    symbol = position.symbol
    ticket = position.ticket
    pip_size, _, _ = get_config(symbol)
    level1, level2 = get_partial_levels(symbol)

    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        return

    if position.type == 0:  # BUY
        profit_pips = (tick.bid - position.price_open) / pip_size
    else:  # SELL
        profit_pips = (position.price_open - tick.ask) / pip_size

    if ticket not in _partial_hit:
        _partial_hit[ticket] = 0

    if _partial_hit[ticket] == 0 and profit_pips >= level1:
        if close_partial_position(position, 0.5, f"+{level1} pips target"):
            _partial_hit[ticket] = 1

    elif _partial_hit[ticket] == 1 and profit_pips >= level2:
        if close_partial_position(position, 0.5, f"+{level2} pips target"):
            _partial_hit[ticket] = 2


def update_trailing_stop(position):
    """
    Move SL in profit direction only — never against the trade.
    Uses pair-specific trail and breakeven distances.
    """
    symbol     = position.symbol
    ticket     = position.ticket
    pos_type   = position.type
    entry      = position.price_open
    current_sl = position.sl
    current_tp = position.tp

    pip_size, trail_pips, breakeven_pips = get_config(symbol)

    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        return False

    current_price = tick.bid if pos_type == 0 else tick.ask

    if pos_type == 0:  # BUY
        profit_pips = (current_price - entry) / pip_size
        new_sl = round(current_price - (trail_pips * pip_size), 5)

        if new_sl <= current_sl:
            return False

        if profit_pips >= breakeven_pips:
            be_sl = round(entry + (MIN_PROFIT_LOCK * pip_size), 5)
            new_sl = max(new_sl, be_sl)

    else:  # SELL
        profit_pips = (entry - current_price) / pip_size
        new_sl = round(current_price + (trail_pips * pip_size), 5)

        if new_sl >= current_sl:
            return False

        if profit_pips >= breakeven_pips:
            be_sl = round(entry - (MIN_PROFIT_LOCK * pip_size), 5)
            new_sl = min(new_sl, be_sl)

    if abs(new_sl - current_sl) < pip_size:
        return False

    request = {
        "action":   mt5.TRADE_ACTION_SLTP,
        "position": ticket,
        "sl":       new_sl,
        "tp":       current_tp,
    }
    result = mt5.order_send(request)
    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
        direction = "BUY" if pos_type == 0 else "SELL"
        print(f"  [Trail] ✅ {symbol} {direction} #{ticket} | "
              f"+{profit_pips:.1f} pips | SL: {current_sl:.5f} → {new_sl:.5f}")
        return True
    else:
        retcode = result.retcode if result else "None"
        print(f"  [Trail] ❌ {symbol} #{ticket} SL failed: {retcode}")
        return False


def close_all_positions(reason="Day-end close"):
    """Close all ForexMind positions."""
    positions = get_forexmind_positions()
    if not positions:
        return 0
    closed = 0
    for pos in positions:
        tick = mt5.symbol_info_tick(pos.symbol)
        if not tick:
            continue
        price      = tick.bid if pos.type == 0 else tick.ask
        order_type = mt5.ORDER_TYPE_SELL if pos.type == 0 else mt5.ORDER_TYPE_BUY
        request = {
            "action":    mt5.TRADE_ACTION_DEAL,
            "position":  pos.ticket,
            "symbol":    pos.symbol,
            "volume":    pos.volume,
            "type":      order_type,
            "price":     price,
            "deviation": 20,
            "magic":     MAGIC_NUMBER,
            "comment":   reason,
        }
        result = mt5.order_send(request)
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            sign = "+" if pos.profit >= 0 else ""
            print(f"  [Trail] ✅ Closed {pos.symbol} #{pos.ticket} | P&L: {sign}${pos.profit:.2f}")
            # Clean up partial tracker
            _partial_hit.pop(pos.ticket, None)
            closed += 1
    return closed


def run_trailing_monitor():
    print("""
╔══════════════════════════════════════════════════════════════╗
║     ForexMind Trailing Stop + Partial Profit (FINAL)         ║
║  Gold:  trail=150 pips | partial: 200/400 pips              ║
║  Forex: trail=30 pips  | partial: 20/40 pips                ║
║  Day-end close: 20:00 UTC | Telegram alerts enabled         ║
║  Press Ctrl+C to stop                                       ║
╚══════════════════════════════════════════════════════════════╝
""")
    print("  Pair settings:")
    for sym, (pip, trail, be) in PAIR_CONFIG.items():
        lvl = PARTIAL_LEVELS.get(sym, PARTIAL_LEVELS["default"])
        print(f"    {sym:<10} trail={trail:3d} pips  "
              f"breakeven={be:2d} pips  partial={lvl[0]}/{lvl[1]} pips")
    print()

    if not connect_mt5():
        print("[Trail] Cannot connect to MT5.")
        return

    send_telegram(
        "🔄 <b>Trailing Stop + Partial Profit Started</b>\n"
        "Gold: 150 pip trail | Partial at 200/400 pips\n"
        f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )

    check_count  = 0
    last_close_h = -1

    while True:
        try:
            check_count += 1
            now_utc = datetime.now(timezone.utc)

            # Day-end close at 20:00 UTC
            if now_utc.hour == 20 and last_close_h != 20:
                print(f"\n  [Trail] ⏰ 20:00 UTC — closing all positions...")
                closed = close_all_positions("Day-end 20:00 UTC")
                if closed > 0:
                    send_telegram(
                        f"🌙 <b>Day-End Close</b>: {closed} position(s) closed\n"
                        f"Next: London open ~08:00 UTC"
                    )
                last_close_h = 20
            elif now_utc.hour != 20:
                last_close_h = -1

            # Get open positions and update
            positions    = get_forexmind_positions()
            open_tickets = {p.ticket for p in positions}

            # Clean up _partial_hit for closed positions
            for ticket in list(_partial_hit.keys()):
                if ticket not in open_tickets:
                    del _partial_hit[ticket]

            if positions:
                for pos in positions:
                    update_trailing_stop(pos)
                    check_partial_profit(pos)

                if check_count % 6 == 0:
                    now_str = datetime.now().strftime("%H:%M:%S")
                    print(f"\n  [{now_str}] {len(positions)} position(s):")
                    for pos in positions:
                        tick = mt5.symbol_info_tick(pos.symbol)
                        if not tick:
                            continue
                        pip_size, _, _ = get_config(pos.symbol)
                        price = tick.bid if pos.type == 0 else tick.ask
                        pips  = ((price - pos.price_open) if pos.type == 0
                                 else (pos.price_open - price)) / pip_size
                        direction = "BUY" if pos.type == 0 else "SELL"
                        sign      = "+" if pos.profit >= 0 else ""
                        partial   = f" [partial L{_partial_hit.get(pos.ticket,0)}]" if pos.ticket in _partial_hit else ""
                        print(f"    {pos.symbol} {direction} #{pos.ticket} | "
                              f"P&L: {sign}{pos.profit:.2f}$ | "
                              f"Pips: {pips:+.1f} | SL: {pos.sl}{partial}")
            else:
                if check_count % 18 == 0:
                    print(f"  [{datetime.now().strftime('%H:%M:%S')}] "
                          f"No open positions. Waiting...")

            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            print("\n\n  Trailing stop monitor stopped.")
            send_telegram("⛔ Trailing Stop Monitor stopped.")
            break
        except Exception as e:
            print(f"  [Trail] Error: {e}")
            time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    run_trailing_monitor()
