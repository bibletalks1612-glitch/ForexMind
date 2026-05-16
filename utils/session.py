"""
ForexMind - Session-Aware Trading Filter
Prevents trading during low-volume sessions.

Sessions (UTC):
  Asian:   23:00-08:00  (low volume — skip EUR/GBP)
  London:  08:00-16:00  (high volume — trade all)
  Overlap: 13:00-16:00  (BEST — highest volume)
  NY:      13:00-21:00  (high volume — trade all)
  Closed:  21:00-23:00  (very low — skip all)
"""

from datetime import datetime, timezone


def get_current_session() -> str:
    """Return current session name based on UTC hour."""
    h = datetime.now(timezone.utc).hour
    if 13 <= h < 16:
        return "overlap"   # London + NY overlap — best
    elif 8 <= h < 16:
        return "london"
    elif 13 <= h < 21:
        return "newyork"
    elif 21 <= h < 23:
        return "closed"
    else:
        return "asian"     # 23:00-08:00 UTC


def get_session_info() -> dict:
    session = get_current_session()
    info = {
        "overlap":  {"session_name": "London/NY Overlap", "volume": "HIGHEST", "trade": True},
        "london":   {"session_name": "London Session",    "volume": "HIGH",    "trade": True},
        "newyork":  {"session_name": "New York Session",  "volume": "HIGH",    "trade": True},
        "asian":    {"session_name": "Asian Session",     "volume": "LOW",     "trade": False},
        "closed":   {"session_name": "Market Closed",     "volume": "VERY LOW","trade": False},
    }
    result = info.get(session, info["asian"])
    result["session"] = session
    return result


# Pairs allowed during Asian session (naturally active)
ASIAN_ALLOWED = {"USD_JPY", "AUD_USD", "NZD_USD", "USD_CAD"}


def should_trade(pair: str) -> tuple:
    """
    Returns (bool, reason) — whether to trade this pair now.
    """
    session = get_current_session()
    info    = get_session_info()

    if session == "closed":
        return False, f"[Session] Market closed (21:00-23:00 UTC) — skipping {pair}"

    if session == "asian":
        pair_key = pair.upper().replace("/", "_")
        if pair_key in ASIAN_ALLOWED:
            return True, f"[Session] Asian session — {pair} is JPY/AUD active pair ✓"
        else:
            return False, f"[Session] Asian session low volume — skipping {pair}"

    # London, NY, Overlap — trade everything
    return True, f"[Session] {info['session_name']} ({info['volume']}) — {pair} ✓"
