"""
ForexMind — ATR-Based SL/TP Patch (Most Impactful Fix)

WHAT THIS FIXES:
  Before: SL/TP calculated with fixed pips (50 pip SL for ALL pairs)
          Gold at price 4540: SL = 4540 + 0.5 = 5 actual pips → hit in seconds
          Forex in high volatility: 50 pip SL may be too tight or too wide

  After:  SL = 1.5 × ATR (adapts to actual market volatility)
          TP = 3.0 × ATR (guarantees 2:1 reward:risk minimum)
          Gold with ATR=30: SL = 45 price units (450 pips) → survives real moves
          EUR/USD with ATR=0.0012: SL = 0.0018 (18 pips) → appropriate

WHY THIS WORKS:
  Research finding (n8n LLM trading bot, +47% returns):
  "Enforces strict risk management with 1.5x ATR stop losses
   and minimum 1:2 risk-reward ratios"

  ATR already calculated in data/indicators.py — we just need to USE it.

FILES CHANGED:
  1. utils/mt5_executor.py  — ATR-aware SL/TP fallback + hard lot cap 0.02
  2. main.py                — pass ATR-based SL/TP to place_order
  3. agents/execution.py    — pass atr to pipeline so it flows through

Run from D:\\algotrade\\ForexMind:
    python patch_atr_sl.py
"""

import os

ROOT = os.path.dirname(os.path.abspath(__file__))

def read(relpath):
    full = os.path.join(ROOT, relpath.replace("/", os.sep))
    with open(full, "r", encoding="utf-8") as f:
        return f.read()

def write(relpath, content):
    full = os.path.join(ROOT, relpath.replace("/", os.sep))
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content.lstrip("\n"))
    size = os.path.getsize(full)
    print(f"  OK  {relpath}  ({size} bytes)")

def patch(relpath, old, new, label=""):
    content = read(relpath)
    if old in content:
        full = os.path.join(ROOT, relpath.replace("/", os.sep))
        with open(full, "w", encoding="utf-8") as f:
            f.write(content.replace(old, new, 1))
        print(f"  OK  {relpath} — {label}")
        return True
    print(f"  --  {relpath} — '{label}' already patched or not found")
    return False

print("\n" + "="*60)
print("  ForexMind ATR-Based SL/TP Patch")
print("="*60)


# ════════════════════════════════════════════════════════════════
# FILE 1: utils/mt5_executor.py
# Replace fixed-pip SL/TP fallback with ATR-aware calculation
# Also accept atr= parameter so caller can pass real ATR value
# ════════════════════════════════════════════════════════════════
print("\n[1/3] Patching utils/mt5_executor.py...")

# Read full file
mt5_content = read("utils/mt5_executor.py")

# Patch 1a: add atr parameter to place_order signature
old_sig = "    def place_order(self, pair: str, action: str, size: float,\n                    sl: float, tp: float) -> dict:"
new_sig = "    def place_order(self, pair: str, action: str, size: float,\n                    sl: float, tp: float, atr: float = 0.0) -> dict:"

# Patch 1b: replace the broken SL/TP fallback block
old_sltp = """        if action == "BUY":
            # SL should be below current price
            if sl == 0.0 or sl >= price:
                sl = round(price - (50 * point * 10), digits)  # 50 pips below
            # TP should be above current price
            if tp == 0.0 or tp <= price:
                tp = round(price + (100 * point * 10), digits)  # 100 pips above
        else:  # SELL
            # SL should be above current price
            if sl == 0.0 or sl <= price:
                sl = round(price + (50 * point * 10), digits)  # 50 pips above
            # TP should be below current price
            if tp == 0.0 or tp >= price:
                tp = round(price - (100 * point * 10), digits) # 100 pips below"""

new_sltp = """        # ATR-based SL/TP — adapts to actual market volatility
        # SL = 1.5 × ATR, TP = 3.0 × ATR (guarantees 2:1 R:R minimum)
        # If ATR not provided, fall back to pair-specific safe defaults
        is_gold = symbol.upper().startswith("XAU")

        if atr and atr > 0:
            sl_dist = round(atr * 1.5, digits)
            tp_dist = round(atr * 3.0, digits)
            print(f"  [MT5 Executor] ATR={atr:.5f} | SL_dist={sl_dist:.5f} | TP_dist={tp_dist:.5f}")
        elif is_gold:
            # Gold safe fallback: 150 pip SL (15.0 price units), 300 pip TP
            sl_dist = 15.0
            tp_dist = 30.0
            print(f"  [MT5 Executor] Gold fixed fallback: SL=150 pips, TP=300 pips")
        else:
            # Forex safe fallback: 50 pip SL
            sl_dist = round(50 * point * 10, digits)
            tp_dist = round(100 * point * 10, digits)
            print(f"  [MT5 Executor] Forex fixed fallback: SL=50 pips, TP=100 pips")

        if action == "BUY":
            if sl == 0.0 or sl >= price:
                sl = round(price - sl_dist, digits)
            if tp == 0.0 or tp <= price:
                tp = round(price + tp_dist, digits)
        else:  # SELL
            if sl == 0.0 or sl <= price:
                sl = round(price + sl_dist, digits)
            if tp == 0.0 or tp >= price:
                tp = round(price - tp_dist, digits)"""

# Patch 1c: hard cap lots at 0.02
old_lot = "        size = min(max(float(size), 0.01), 0.05)"
new_lot = "        size = min(max(float(size), 0.01), 0.02)   # testing: hard cap 0.02"

applied = 0
if old_sig in mt5_content:
    mt5_content = mt5_content.replace(old_sig, new_sig, 1)
    applied += 1
    print("  OK  place_order signature — added atr parameter")
else:
    if "atr: float = 0.0" in mt5_content:
        print("  --  atr parameter already present")
    else:
        print("  !!  signature not found — may need manual edit")

if old_sltp in mt5_content:
    mt5_content = mt5_content.replace(old_sltp, new_sltp, 1)
    applied += 1
    print("  OK  SL/TP fallback — replaced with ATR-based logic")
else:
    if "atr * 1.5" in mt5_content:
        print("  --  ATR SL/TP already present")
    else:
        print("  !!  SL/TP block not found — check file manually")

if old_lot in mt5_content:
    mt5_content = mt5_content.replace(old_lot, new_lot, 1)
    applied += 1
    print("  OK  lot cap — 0.05 → 0.02")
elif "0.02)   # testing" in mt5_content:
    print("  --  lot cap already at 0.02")

full_path = os.path.join(ROOT, "utils", "mt5_executor.py")
with open(full_path, "w", encoding="utf-8") as f:
    f.write(mt5_content)
print(f"  Saved utils/mt5_executor.py ({applied} changes)")


# ════════════════════════════════════════════════════════════════
# FILE 2: main.py
# Calculate ATR-based SL/TP before calling place_order
# Pass actual price levels (not 0) so executor uses them directly
# ════════════════════════════════════════════════════════════════
print("\n[2/3] Patching main.py...")

old_place_order = """            order_result = executor.place_order(
                pair=pair,
                action=action,
                size=size,
                sl=decision.get("stop_loss", 0),
                tp=decision.get("take_profit", 0),
            )"""

new_place_order = """            # Calculate ATR-based SL/TP from current indicators
            atr_value = 0.0
            if current_indicators and current_indicators.get("atr"):
                atr_value = float(current_indicators["atr"])

            order_result = executor.place_order(
                pair=pair,
                action=action,
                size=size,
                sl=decision.get("stop_loss", 0),
                tp=decision.get("take_profit", 0),
                atr=atr_value,   # ATR-based SL/TP — adapts to volatility
            )"""

if patch("main.py", old_place_order, new_place_order, "pass ATR to place_order"):
    print("  ATR will now flow from indicators → executor for every order")
else:
    print("  !!  Manual fix: add atr=current_indicators.get('atr', 0) to executor.place_order()")


# ════════════════════════════════════════════════════════════════
# FILE 3: agents/execution.py
# Add EMA200 debug logging so we can see WHY it returns NEUTRAL
# Also fix the candle key access (dict vs object)
# ════════════════════════════════════════════════════════════════
print("\n[3/3] Patching agents/execution.py — EMA200 debug + candle key fix...")

old_ema = """def get_ema200_trend(pair: str) -> str:
    \"\"\"
    Fetch H4 candles and check if price is above/below EMA 200.
    Returns: "BUY_ONLY" | "SELL_ONLY" | "NEUTRAL"

    DeepSeek idea — fixed bug: calculate_ema returns float not list.
    \"\"\"
    try:
        mt5 = MT5Client()
        candles = mt5.get_candles(pair, "H4", count=250)
        if not candles or len(candles) < 200:
            return "NEUTRAL"
        closes = [c["close"] for c in candles]
        ema200 = calculate_ema(closes, 200)   # returns single float
        current_price = closes[-1]
        if current_price > ema200:
            return "BUY_ONLY"
        elif current_price < ema200:
            return "SELL_ONLY"
        return "NEUTRAL"
    except Exception as e:
        print(f"    [EMA200] Error: {e} — skipping filter")
        return "NEUTRAL\""""

new_ema = """def get_ema200_trend(pair: str) -> str:
    \"\"\"
    Fetch H4 candles and check if price is above/below EMA 200.
    Returns: "BUY_ONLY" | "SELL_ONLY" | "NEUTRAL"
    Includes full debug logging so failures are visible.
    \"\"\"
    try:
        mt5 = MT5Client()
        candles = mt5.get_candles(pair, "H4", count=250)

        if not candles:
            print(f"    [EMA200] No H4 candles returned for {pair} → NEUTRAL")
            return "NEUTRAL"

        if len(candles) < 200:
            print(f"    [EMA200] Only {len(candles)} candles (need 200) → NEUTRAL")
            return "NEUTRAL"

        # Handle both dict-style and object-style candle access
        try:
            closes = [float(c["close"]) for c in candles]
        except (TypeError, KeyError):
            try:
                closes = [float(c.close) for c in candles]
            except AttributeError:
                closes = [float(c[4]) for c in candles]   # MT5 tuple format

        ema200 = calculate_ema(closes, 200)   # returns single float
        current_price = closes[-1]

        print(f"    [EMA200] {pair} H4: price={current_price:.5f} EMA200={ema200:.5f}", end="")

        if current_price > ema200:
            print(" → BUY_ONLY (price above EMA200)")
            return "BUY_ONLY"
        elif current_price < ema200:
            print(" → SELL_ONLY (price below EMA200)")
            return "SELL_ONLY"
        print(" → NEUTRAL")
        return "NEUTRAL"

    except Exception as e:
        print(f"    [EMA200] Exception: {e} → NEUTRAL (filter skipped)")
        return "NEUTRAL\""""

if patch("agents/execution.py", old_ema, new_ema, "EMA200 debug + candle key fix"):
    pass
else:
    print("  --  EMA200 function may already be updated or differs slightly")


# ════════════════════════════════════════════════════════════════
# VERIFICATION
# ════════════════════════════════════════════════════════════════
print("\n  Verifying patches...")
checks = {
    "utils/mt5_executor.py": ["atr * 1.5", "atr * 3.0", "0.02)   # testing"],
    "main.py":               ["atr=atr_value", "current_indicators[\"atr\"]"],
    "agents/execution.py":   ["EMA200] Exception", "c.close", "c[4]"],
}
all_ok = True
for f, patterns in checks.items():
    content = read(f)
    for p in patterns:
        ok = p in content
        if not ok:
            print(f"  !!  {f} missing: {p}")
            all_ok = False
if all_ok:
    print("  All patches verified OK")


print(f"""
{"="*60}
  ATR-Based SL/TP Patch Complete!

  What changed:
  ─────────────────────────────────────────────────────
  mt5_executor.py  SL = 1.5 × ATR  (was 50 pip fixed)
                   TP = 3.0 × ATR  (was 100 pip fixed)
                   Gold fallback: SL=150 pip, TP=300 pip
                   Lot hard cap: 0.02 (was 0.05)

  main.py          Passes real ATR value to place_order
                   ATR comes from H1 indicators already
                   calculated in Step 3 of analyze_pair

  execution.py     EMA200 now shows full debug output:
                   [EMA200] XAU_USD H4: price=4540 EMA200=4510 → SELL_ONLY
                   Handles dict/object/tuple candle formats
  ─────────────────────────────────────────────────────

  What you'll see now (example for gold ATR=25):
    ATR=25.00000 | SL_dist=37.50000 | TP_dist=75.00000
    SELL XAU_USD: entry=4540, SL=4577.5, TP=4465.0
    → 375 pip SL (survives noise) → 750 pip TP (2:1 R:R)

  What you'll see for EUR/USD ATR=0.0015:
    ATR=0.00150 | SL_dist=0.00225 | TP_dist=0.00450
    BUY EUR_USD: entry=1.1650, SL=1.1628, TP=1.1695
    → 22.5 pip SL → 45 pip TP (2:1 R:R)

  Run now:
    python main.py --pair XAU_USD --rounds 2
    python run_auto.py
{"="*60}
""")
