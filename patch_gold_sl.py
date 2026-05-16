"""
ForexMind — CRITICAL Gold SL/TP Fix
This is the ROOT CAUSE of all gold losses.

THE BUG:
  mt5_executor.py uses: 50 * point * 10 for SL
  For gold: point = 0.01, so 50 * 0.01 * 10 = 0.5 price units = ~5 pips
  Gold at 4540 moves 50 pips in SECONDS — SL gets hit immediately
  This caused: -15.00, -23.66, -12.08 losses in rapid succession

THE FIX:
  Gold needs: 150 pip SL minimum (price units = 150 * 0.1 = 15.0)
  Gold TP: 300 pips minimum (price units = 300 * 0.1 = 30.0)
  Also: hard cap lot size at 0.02 (was 0.05)

Run from D:\\algotrade\\ForexMind:
    python patch_gold_sl.py
"""

import os

ROOT = os.path.dirname(os.path.abspath(__file__))

def read(relpath):
    full = os.path.join(ROOT, relpath.replace("/", os.sep))
    with open(full, "r", encoding="utf-8") as f:
        return f.read()

def write_file(relpath, content):
    full = os.path.join(ROOT, relpath.replace("/", os.sep))
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)
    size = os.path.getsize(full)
    print(f"  ✅  {relpath}  ({size} bytes)")

print("\n" + "="*60)
print("  ForexMind CRITICAL Gold SL/TP Fix")
print("="*60)

# ── Read current mt5_executor.py ──────────────────────────────
content = read("utils/mt5_executor.py")

# ── Show current SL/TP values so user can see what changed ────
print("\n  Current SL/TP logic (WRONG for gold):")
for line in content.split("\n"):
    if "50 * point" in line or "100 * point" in line:
        print(f"    {line.strip()}")

# ── THE FIX ───────────────────────────────────────────────────
# Replace the SL/TP block with gold-aware version

OLD_SLTP = """        # Auto-calculate SL/TP if invalid or unrealistic
        if action == "BUY":
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

NEW_SLTP = """        # Auto-calculate SL/TP if invalid or unrealistic
        # GOLD FIX: point=0.01 for XAUUSD so multiply differently
        # Gold:  1 pip = 0.1 price units.  We want 150 pip SL = 15.0 units
        # Forex: 1 pip = point*10.         We want 50 pip SL = 50*point*10
        is_gold = symbol.upper().startswith("XAU")

        if is_gold:
            sl_distance = 150 * 0.1   # = 15.0 price units (150 pips)
            tp_distance = 300 * 0.1   # = 30.0 price units (300 pips)
        else:
            sl_distance = 50  * point * 10   # standard forex 50 pips
            tp_distance = 100 * point * 10   # standard forex 100 pips

        if action == "BUY":
            if sl == 0.0 or sl >= price:
                sl = round(price - sl_distance, digits)
            if tp == 0.0 or tp <= price:
                tp = round(price + tp_distance, digits)
        else:  # SELL
            if sl == 0.0 or sl <= price:
                sl = round(price + sl_distance, digits)
            if tp == 0.0 or tp >= price:
                tp = round(price - tp_distance, digits)"""

OLD_LOT = "        size = min(max(float(size), 0.01), 0.05)"
NEW_LOT = "        size = min(max(float(size), 0.01), 0.02)   # testing: hard cap 0.02 lots"

# Apply SL/TP fix
if OLD_SLTP in content:
    content = content.replace(OLD_SLTP, NEW_SLTP, 1)
    print("\n  ✅ Gold-aware SL/TP block applied")
else:
    print("\n  ⚠️  SL/TP pattern not found exactly.")
    print("     Manual fix needed — see instructions below.")

# Apply lot cap fix
if OLD_LOT in content:
    content = content.replace(OLD_LOT, NEW_LOT, 1)
    print("  ✅ Lot size hard cap: 0.05 → 0.02")
elif "0.02)   # testing" in content:
    print("  ✅ Lot size cap already at 0.02 — no change needed")
else:
    print("  ⚠️  Lot size pattern not found — check manually")

write_file("utils/mt5_executor.py", content)

# ── Verify the fix was applied ────────────────────────────────
print("\n  Verifying fix...")
verify = read("utils/mt5_executor.py")
if "is_gold" in verify and "150 * 0.1" in verify:
    print("  ✅ Gold SL fix confirmed in file")
else:
    print("  ❌ Fix not found — manual patch needed")
    print("\n  MANUAL FIX: Open utils/mt5_executor.py")
    print("  Find the BUY/SELL SL/TP block and replace with:")
    print("""
        is_gold = symbol.upper().startswith("XAU")
        if is_gold:
            sl_distance = 15.0   # 150 pips for gold
            tp_distance = 30.0   # 300 pips for gold
        else:
            sl_distance = 50 * point * 10
            tp_distance = 100 * point * 10

        if action == "BUY":
            if sl == 0.0 or sl >= price:
                sl = round(price - sl_distance, digits)
            if tp == 0.0 or tp <= price:
                tp = round(price + tp_distance, digits)
        else:
            if sl == 0.0 or sl <= price:
                sl = round(price + sl_distance, digits)
            if tp == 0.0 or tp >= price:
                tp = round(price - tp_distance, digits)
""")

print(f"""
{"="*60}
  What this fixes:

  BEFORE (causing losses):
    Gold SELL SL = price + (50 * 0.01 * 10) = price + 0.5
    At price 4540: SL = 4540.50  (only 5 pips above!)
    Gold moves 50 pips in seconds → immediate stop-out

  AFTER (correct):
    Gold SELL SL = price + 15.0  (150 pips above)
    At price 4540: SL = 4555.0
    Gold needs 150 pip move to stop out → survives noise

  Gold SL/TP summary:
    SL: 150 pips = $15 max loss per 0.01 lot trade
    TP: 300 pips = $30 max gain per 0.01 lot (2:1 R:R)
    Lot cap: 0.02 max

  Also note: the bot was SELLING gold while gold is RISING.
  The EMA200 filter in execution.py should block this.
  If it's still happening, check that execution.py has the
  EMA200 filter active — it should show:
    [Portfolio Manager] EMA200 says BUY_ONLY — blocking SELL

  After applying this fix:
    python main.py --pair XAU_USD --rounds 2
    python run_auto.py
{"="*60}
""")
