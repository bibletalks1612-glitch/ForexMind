# ForexMind v2 Configuration
# Enhanced settings for multi-timeframe analysis, session trading, and risk management

import os
from datetime import datetime

# ============ LLM & API KEYS ============
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "your_groq_key")
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY", "your_cerebras_key")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "your_gemini_key")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "your_telegram_token")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "your_chat_id")

# ============ MT5 CREDENTIALS ============
MT5_ACCOUNT = int(os.getenv("MT5_ACCOUNT", "123456789"))
MT5_PASSWORD = os.getenv("MT5_PASSWORD", "your_password")
MT5_SERVER = os.getenv("MT5_SERVER", "MetaQuotes-Demo")
MT5_PATH = os.getenv("MT5_PATH", "C:\\Program Files\\MetaTrader 5\\terminal64.exe")

# ============ TRADING PAIRS ============
TRADING_PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "NZDUSD"]
BASE_LOT_SIZE = 0.01  # 0.01 lots per position

# ============ TIMEFRAME ANALYSIS ============
TIMEFRAMES = ["H1", "H4", "D1"]  # Analysis timeframes
PRIMARY_TIMEFRAME = "H1"  # Entry signals from H1
CONFLUENCE_TIMEFRAMES = ["H1", "H4"]  # For multi-timeframe confluence

# ============ CONFLUENCE & RISK SETTINGS ============
MIN_CONFLUENCE_SCORE = 60  # 0-100: Below this, reduce position size 50%
HIGH_CONFLUENCE_SCORE = 80  # Above this, allow full position size
CONFLUENCE_POSITION_FACTOR_LOW = 0.5   # Position size when confluence < 60
CONFLUENCE_POSITION_FACTOR_MED = 0.75  # Position size when 60-80
CONFLUENCE_POSITION_FACTOR_HIGH = 1.0  # Position size when > 80

# ============ SESSION TRADING SETTINGS ============
PREFERRED_SESSIONS = ["london", "newyork", "overlap"]  # Trade during these sessions
AVOID_SESSIONS = ["asian"]  # Skip trading during these sessions
SESSION_POSITION_MULTIPLIER = 0.5  # 50% position size outside preferred sessions

# Session definitions (UTC times)
SESSIONS = {
    "asian": {"start": 22, "end": 8},      # 10 PM - 8 AM UTC (Tokyo open)
    "london": {"start": 8, "end": 16},     # 8 AM - 4 PM UTC
    "newyork": {"start": 13, "end": 21},   # 1 PM - 9 PM UTC
    "overlap": {"start": 8, "end": 12}     # 8 AM - 12 PM UTC (London + NY overlap)
}

# ============ STOP LOSS & TAKE PROFIT ============
ATR_PERIOD = 14
ATR_STOP_LOSS_MULTIPLIER = 2.0  # SL = 2 x ATR
ATR_TAKE_PROFIT_MULTIPLIER = 3.0  # TP = 3 x ATR
TRAILING_STOP_ATR_MULTIPLIER = 1.5  # Trail = 1.5 x ATR (adapts to volatility)

FIXED_STOP_LOSS_PIPS = 50  # Fallback if ATR unavailable
FIXED_TAKE_PROFIT_PIPS = 100  # Fallback if ATR unavailable

# ============ LOSS HANDLING (ENHANCED) ============
MAX_DAILY_LOSS_USD = -500  # Max loss before stopping trades for the day
MAX_WEEKLY_LOSS_USD = -2000  # Max loss before reducing position sizes
MAX_MONTHLY_LOSS_USD = -5000  # Max loss before risk reset

LOSS_HANDLING_MODE = "progressive"  # "strict" | "progressive"
# strict: Stop trading on loss threshold
# progressive: Reduce position size as losses increase

LOSS_THRESHOLD_MULTIPLIERS = {
    "normal": 1.0,        # Full position size (no losses yet)
    "caution": 0.75,      # 75% at -250 USD loss
    "warning": 0.5,       # 50% at -500 USD loss
    "danger": 0.25,       # 25% at -1000 USD loss
    "halt": 0.0           # Stop trading at -2000 USD loss
}

# ============ ECONOMIC CALENDAR FILTER ============
ECONOMIC_CALENDAR_ENABLED = True
EVENT_AVOIDANCE_MINUTES = 30  # Skip trading 30 mins before/after high-impact events
CALENDAR_DATA_SOURCE = "forexfactory"  # or "investing.com"

# High-impact events to monitor
HIGH_IMPACT_EVENTS = [
    "NFP",  # Non-Farm Payroll (US)
    "CPI",  # Consumer Price Index
    "ECB",  # European Central Bank Decision
    "FOMC",  # US Fed Decision
    "BOE",  # Bank of England Decision
    "RBA",  # Reserve Bank of Australia
    "Unemployment",
    "Retail Sales"
]

# ============ AUTO CLOSE SETTINGS ============
AUTO_CLOSE_DAY_END_ENABLED = True
AUTO_CLOSE_TIME_GMT = "21:00"  # Close all positions at 9 PM GMT
AUTO_OPEN_TIME_GMT = "08:30"  # Resume trading at 8:30 AM GMT
SKIP_WEEKENDS = True  # Don't trade Friday evening through Sunday evening

# ============ CONFIDENCE & DECISION THRESHOLDS ============
MIN_DEBATE_CONFIDENCE = 60  # Only take trades if debate confidence > 60%
MIN_COMBINED_CONFIDENCE = 70  # (debate + confluence + session + calendar)

# Debate analyst contributions to confidence
DEBATE_WEIGHT = 0.40  # 40% of total confidence
CONFLUENCE_WEIGHT = 0.30  # 30% of total confidence
SESSION_WEIGHT = 0.15  # 15% of total confidence
CALENDAR_WEIGHT = 0.15  # 15% of total confidence

# ============ BACKTEST SETTINGS ============
BACKTEST_START_DATE = "2025-01-01"
BACKTEST_END_DATE = "2026-05-14"
BACKTEST_PAIRS = ["EURUSD", "GBPUSD"]
BACKTEST_TIMEFRAME = "H1"
BACKTEST_INITIAL_BALANCE = 100000  # USD

# ============ CALIBRATION SETTINGS ============
CALIBRATION_ENABLED = True
CALIBRATION_LOOKBACK_TRADES = 20  # Analyze last 20 trades
CALIBRATION_ADJUSTMENT_MAX = 15  # Max confidence adjustment: ±15%

# ============ DASHBOARD SETTINGS ============
DASHBOARD_HOST = "127.0.0.1"
DASHBOARD_PORT = 8080
DASHBOARD_REFRESH_INTERVAL = 5  # seconds
DASHBOARD_ENABLED = True

# ============ INDIAN MARKET INTEGRATION (FUTURE) ============
INDIAN_MARKET_ENABLED = False  # Set to True when Indian stock module is ready
INDIAN_SYMBOLS = ["SBIN", "RELIANCE", "TCS", "INFY", "HDFC"]
INDIAN_MARKET_OPEN_IST = "09:15"  # 9:15 AM IST
INDIAN_MARKET_CLOSE_IST = "15:30"  # 3:30 PM IST
OPENALGO_ENABLED = False  # Shoonya/OpenAlgo integration

# ============ LOGGING & MEMORY ============
MEMORY_FILE = "memory/data/decisions.json"
CALIBRATION_FILE = "memory/calibration.json"
TRADE_LOG_FILE = "memory/trades.log"
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR

# ============ TELEGRAM ALERTS ============
SEND_TRADE_ALERTS = True
SEND_LOSS_ALERTS = True
SEND_CALENDAR_ALERTS = True
SEND_SESSION_ALERTS = False  # Noisy, disable if not needed
SEND_CALIBRATION_ALERTS = True

print(f"✓ ForexMind v2 Configuration Loaded ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC)")
