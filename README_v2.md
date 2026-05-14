# ForexMind v2 — Complete Enhancement Guide

## Overview
ForexMind v2 is a production-ready multi-agent AI forex trading bot with 10 major enhancements over v1. It uses 4 analyst agents + Bull/Bear debate + advanced risk management to place trades on MT5 demo accounts.

## What's New in v2

### ✅ Enhancement 1: Fixed Debate Output Format
- **Status:** Complete ✓
- **File:** `agents/researchers.py`
- **What:** Fixed debate_result format to return `{lean, confidence, transcript}`
- **Impact:** Main.py now receives properly formatted debate decisions

### ✅ Enhancement 2: Multi-Timeframe Confluence Scoring
- **Status:** Complete ✓
- **File:** `data/indicators.py`
- **What:** Scores agreement between H1, H4, D1 timeframes (0-100)
- **Impact:** 
  - Confluence < 60: 50% position size (high risk)
  - Confluence 60-80: 75% position size (moderate)
  - Confluence > 80: 100% position size (low risk)

### ✅ Enhancement 3: Session-Aware Trading
- **Status:** Complete ✓
- **File:** `utils/session.py`
- **What:** Detects forex trading sessions (London, New York, Asian, Overlap)
- **Impact:**
  - Preferred sessions: Full position size
  - Asian session: 50% position size (low liquidity)
  - Outside trading hours: Skip trading

### ✅ Enhancement 4: Economic Calendar Filter
- **Status:** Complete ✓
- **File:** `utils/calendar.py`
- **What:** Fetches high-impact events from Forex Factory
- **Impact:** Skips trades 30 mins before/after NFP, CPI, rate decisions, etc.

### ✅ Enhancement 5: Performance Dashboard
- **Status:** Complete ✓
- **Files:** `dashboard/app.py`, `dashboard/templates/dashboard.html`
- **What:** Flask web UI showing real-time trading metrics
- **Run:** `python dashboard/app.py`
- **Features:**
  - Live equity curve chart
  - P&L by symbol breakdown
  - Current open positions table
  - Recent trades history
  - Win rate, profit factor, drawdown

### ✅ Enhancement 6: ATR-Based Dynamic Trailing Stops
- **Status:** Complete ✓
- **File:** `utils/trailing_stop.py`
- **What:** Adapts trailing stop to market volatility using ATR(14)
- **Impact:** Instead of fixed 20-pips, trail = 1.5x ATR (adapts automatically)

### ✅ Enhancement 7: Auto Close at Day-End
- **Status:** Complete ✓
- **File:** `utils/day_close.py`
- **What:** Closes all positions at 21:00 GMT to avoid overnight swap charges
- **Impact:** Prevents rollover losses, improves daily P&L

### ✅ Enhancement 8: Backtesting Module
- **Status:** Complete ✓
- **File:** `backtest/run_backtest.py`
- **What:** Tests strategy on historical MT5 data
- **Run:** `python main.py backtest EURUSD 30`
- **Reports:** Win rate, max drawdown, Sharpe ratio, total return

### ✅ Enhancement 9: Confidence Calibration
- **Status:** Complete ✓
- **File:** `memory/calibrator.py`
- **What:** Records predicted vs actual outcomes, adjusts thresholds
- **Example:** If AI says 70% confidence but only wins 50% → recommend 80%
- **Run:** `python main.py calibrate`

### ✅ Enhancement 10: Enhanced Loss Management
- **Status:** Complete ✓
- **File:** `memory/loss_manager.py`
- **What:** Progressive position reduction based on cumulative losses
- **Thresholds:**
  - Daily loss > $500: Stop trading
  - Daily loss > $250: 75% position size
  - Weekly loss > $2000: 50% position size
  - Monthly loss > $5000: Risk reset

## Quick Start

### 1. Installation
```bash
cd Forexmind
pip install -r requirements.txt
```

### 2. Configuration
Edit `config/settings.py`:
```python
# MT5 Credentials
MT5_ACCOUNT = your_account_number
MT5_PASSWORD = your_password
MT5_SERVER = "MetaQuotes-Demo"

# LLM APIs
GROQ_API_KEY = "your_groq_key"
CEREBRAS_API_KEY = "your_cerebras_key"
GEMINI_API_KEY = "your_gemini_key"

# Telegram
TELEGRAM_BOT_TOKEN = "your_bot_token"
TELEGRAM_CHAT_ID = "your_chat_id"

# Trading Settings
TRADING_PAIRS = ["EURUSD", "GBPUSD", "USDJPY"]
BASE_LOT_SIZE = 0.01
MIN_DEBATE_CONFIDENCE = 65
```

### 3. Run Trading Bot
```bash
python main.py
```

### 4. View Dashboard
```bash
python dashboard/app.py
# Open: http://localhost:8080
```

### 5. Run Backtest
```bash
python main.py backtest EURUSD 30
```

### 6. View Calibration Report
```bash
python main.py calibrate
```

## File Structure

```
Forexmind/
├── agents/
│   ├── analysts.py          # Technical analysis agents
│   ├── researchers.py       # Bull vs Bear debate ✨ FIXED
│   └── execution.py         # Risk manager + position sizing
├── backtest/
│   └── run_backtest.py      # ✨ NEW - Historical testing
├── config/
│   ├── settings.py          # ✨ ENHANCED - All v2 settings
│   └── pair_config.py       # Per-pair settings
├── dashboard/
│   ├── app.py              # ✨ NEW - Flask web server
│   └── templates/
│       └── dashboard.html   # ✨ NEW - Beautiful UI
├── data/
│   ├── fetcher.py          # MT5 data loading
│   └── indicators.py        # ✨ ENHANCED - Confluence scoring
├── memory/
│   ├── manager.py          # Decision tracking
│   ├── loss_manager.py      # ✨ NEW - Loss handling
│   └── calibrator.py        # ✨ NEW - Confidence calibration
├── utils/
│   ├── calendar.py          # ✨ NEW - Economic calendar
│   ├── day_close.py         # ✨ NEW - Auto day-end close
│   ├── llm.py              # LLM API calls
│   ├── mt5_executor.py     # MT5 order execution
│   ├── session.py          # ✨ NEW - Session detection
│   ├── telegram.py         # Telegram notifications
│   └── trailing_stop.py    # ✨ ENHANCED - ATR-based trails
├── main.py                 # ✨ ENHANCED - Main entry point
├── requirements.txt         # ✨ NEW - Python dependencies
└── README.md              # This file
```

## Key Metrics & Configuration

### Loss Management (Your P&L Control)
```
Daily Loss:    -$500 → Stop trading
Weekly Loss:   -$2,000 → Reduce to 50% position
Monthly Loss:  -$5,000 → Risk reset
```

### Confidence Thresholds
```
Debate Confidence:      ≥60% (from Bull/Bear debate)
Confluence Confluence:  60-100% (from multi-timeframe)
Session Quality:        100% (preferred) or 50% (avoided)
Economic Calendar:      100% (clear) or 40% (event nearby)

Final = 40% debate + 30% confluence + 15% session + 15% calendar
Trade only if: Final ≥ MIN_COMBINED_CONFIDENCE (70%)
```

### Position Sizing Multipliers
```
Base Position:  0.01 lots

× Confluence Factor:  (0.5 - 1.0)
× Session Factor:     (0.5 - 1.0)
× Loss Factor:        (0.0 - 1.0)  ← Decreased during drawdowns
× Calendar Factor:    (0.5 or 1.0)  ← Reduced near events

Final = Base × Confluence × Session × Loss × Calendar
```

## Advanced Usage

### Running Backtests
```bash
# Test EURUSD over last 30 days
python main.py backtest EURUSD 30

# Test GBPUSD over 60 days
python main.py backtest GBPUSD 60
```

### Viewing Calibration
```bash
python main.py calibrate

Output:
  50-60%:  45 trades, 18 correct, 40.0% accuracy
  60-70%:  92 trades, 56 correct, 60.9% accuracy  ← BEST
  70-80%:  103 trades, 58 correct, 56.3% accuracy
  80-90%:  67 trades, 34 correct, 50.7% accuracy
  90-100%: 23 trades, 10 correct, 43.5% accuracy
  
  Recommended Threshold: 65% (up from 60%)
  Expected Win Rate Improvement: +4.9%
```

### Dashboard Access
```
http://localhost:8080

Shows:
- Equity curve over time
- P&L by trading pair
- Open positions with current P&L
- Last 20 trades with outcomes
- Overall statistics (win rate, profit factor, etc.)

Refreshes every 5 seconds with live data
```

## Telegram Alerts

Bot sends real-time alerts:
```
✅ EURUSD BUY | Confidence: 78% | Position: 0.01L
⚠️ SKIP GBPUSD — NFP in 25 minutes
📊 Day-end auto-close: 3 positions closed
🚫 Weekly loss limit: $2,104 — Position size reduced to 50%
🤖 Calibration update: Threshold adjusted 70% → 75%
```

## Troubleshooting

### MT5 Connection Failed
```python
# Check settings.py
MT5_PATH = "C:\\Program Files\\MetaTrader 5\\terminal64.exe"
MT5_ACCOUNT = 123456789  # Your account number
MT5_PASSWORD = "your_password"
MT5_SERVER = "MetaQuotes-Demo"  # Or your broker's server
```

### Missing LLM Responses
```python
# Check API keys in settings.py
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")

# Or set environment variables:
export GROQ_API_KEY="gsk_..."
export CEREBRAS_API_KEY="..."
```

### Dashboard Not Loading
```bash
# Check Flask is running
python dashboard/app.py

# Check port 8080 is available
lsof -i :8080

# View logs
tail -f memory/trades.log
```

## Performance Optimization Tips

1. **Confluence Score** — Set higher thresholds during low-liquidity periods
2. **Session Filter** — Avoid Asian session (11pm-7am UTC) for tight spreads
3. **Economic Calendar** — Pre-filter events you care about in settings.py
4. **Loss Management** — Adjust thresholds based on your risk tolerance
5. **Calibration** — Review every 50 trades, adjust confidence thresholds
6. **ATR Period** — Use ATR(14) for H1, ATR(21) for H4

## Next Steps (Enhancement 10)

Instead of Enhancement 10 (Indian markets), consider:
- [ ] Add machine learning confidence prediction
- [ ] Implement order clustering/smart execution
- [ ] Multi-broker support (Alpaca, IB, etc.)
- [ ] Advanced portfolio optimization
- [ ] Risk parity position sizing
- [ ] Regime detection (trending vs ranging)

## Support & Issues

For bugs or feature requests:
1. Check memory/trades.log for errors
2. Review config/settings.py for correct API keys
3. Run backtest to validate strategy logic
4. Check calibration accuracy before trading live

---

**ForexMind v2** — Professional-Grade AI Forex Trading  
*With enhanced risk management, calibration, and monitoring.*
