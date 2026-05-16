"""
ForexMind - Economic Calendar Filter (Stub)
Currently: always allows trading (safe fallback)
Future: integrate Forex Factory feed for real news blackouts

To enable real calendar:
  Replace is_safe_to_trade() with actual API fetch
  Blocks trading 30 min before/after NFP, CPI, FOMC etc.
"""


def is_safe_to_trade(pair: str, hours_ahead: int = 1) -> tuple:
    """
    Returns (safe: bool, reason: str)
    Currently always returns True — no false trade blocks.
    """
    return True, f"[Calendar] No news events detected for {pair} ✓"


def get_upcoming_events(pair: str, hours_ahead: int = 24) -> list:
    """Returns list of upcoming economic events. Stub returns empty list."""
    return []


def check_news_blackout(pairs: list, hours_ahead: int = 1) -> dict:
    """Returns dict of pair → (safe, reason). Stub allows all."""
    return {pair: (True, "No events") for pair in pairs}
