"""
ForexMind - Bull vs Bear Debate Engine (SUPERBOT FINAL)
FIXED: All time.sleep() removed — was causing asyncio.CancelledError
Full v3 logic: confluence + volatility + pair-specific handling
"""

from typing import Dict
from utils.llm import GroqClient


def _conviction_score(text: str) -> tuple:
    t = text.upper()
    if "STRONG" in t and "CONVICTION" in t:
        return "STRONG", 2
    elif "STRONG" in t or "HIGHLY CONFIDENT" in t or "COMPELLING" in t:
        return "STRONG", 2
    elif "WEAK" in t or "UNCERTAIN" in t or "QUESTIONABLE" in t:
        return "WEAK", 0
    return "MODERATE", 1


def _market_context(indicators: dict, pair: str) -> str:
    if not indicators:
        return ""
    trend        = indicators.get("trend", "UNKNOWN")
    rsi          = indicators.get("rsi", 50)
    price_vs_ema = indicators.get("price_vs_ema9", 0)
    atr          = indicators.get("atr", 0)
    macd_hist    = indicators.get("macd", {}).get("histogram", 0)
    stoch_k      = indicators.get("stochastic", {}).get("k", 50)

    trend_icon   = "UP" if trend == "BULLISH" else "DOWN" if trend == "BEARISH" else "FLAT"
    rsi_note     = "OVERBOUGHT" if rsi > 70 else "OVERSOLD" if rsi < 30 else "NEUTRAL"
    ema_note     = "above trend" if price_vs_ema > 0 else "below trend"
    vol          = "HIGH" if atr > 50 else "MEDIUM" if atr > 25 else "LOW"
    macd_note    = "bullish" if macd_hist > 0 else "bearish"
    stoch_note   = "overbought" if stoch_k > 80 else "oversold" if stoch_k < 20 else "neutral"
    pair_note    = ""
    if "XAU" in pair:
        pair_note = "NOTE: Gold - high volatility, require strong confluence for entry."
    elif "GBP" in pair:
        pair_note = "NOTE: GBP - wide spreads, require 150+ pip target."

    return (
        f"MARKET CONTEXT [{pair}]:\n"
        f"  Trend: {trend} ({trend_icon}) | RSI: {rsi:.0f} ({rsi_note})\n"
        f"  Price vs EMA9: {price_vs_ema:+.2f}% ({ema_note}) | ATR: {atr:.2f} ({vol} vol)\n"
        f"  MACD: {macd_note} | Stochastic: {stoch_k:.0f} ({stoch_note})\n"
        f"  {pair_note}\n"
    )


def _tech_bias(indicators: dict) -> tuple:
    if not indicators:
        return "NEUTRAL", 0
    bull = 0
    bear = 0
    trend     = indicators.get("trend", "NEUTRAL")
    rsi       = indicators.get("rsi", 50)
    ema_delta = indicators.get("price_vs_ema9", 0)
    macd_hist = indicators.get("macd", {}).get("histogram", 0)

    if trend == "BULLISH":     bull += 1
    elif trend == "BEARISH":   bear += 1
    if rsi < 30:               bull += 1
    elif rsi > 70:             bear += 1
    if ema_delta > 0:          bull += 1
    elif ema_delta < 0:        bear += 1
    if macd_hist > 0:          bull += 1
    elif macd_hist < 0:        bear += 1

    if bull > bear:   return "BULLISH", bull
    if bear > bull:   return "BEARISH", bear
    return "NEUTRAL", max(bull, bear)


async def run_debate(pair: str, analyst_reports: Dict[str, str],
                     debate_rounds: int, llm: GroqClient,
                     current_indicators: dict = None) -> dict:
    """
    Run Bull vs Bear debate with full market context.
    Returns dict: {lean, confidence, transcript, bull_score, bear_score,
                   technical_bias, confluence_level, market_volatility,
                   pair_specific_risk, rounds}
    """

    print(f"\n  Bull vs Bear Debate: {pair} ({debate_rounds} rounds)")

    combined = "\n\n".join([
        f"=== {name.upper()} ===\n{report[:450]}"
        for name, report in analyst_reports.items()
    ])
    context     = _market_context(current_indicators, pair)
    tech_bias, confluence = _tech_bias(current_indicators)
    atr         = current_indicators.get("atr", 0) if current_indicators else 0
    volatility  = "HIGH" if atr > 50 else "MEDIUM" if atr > 25 else "LOW"
    pair_risk   = "HIGH" if "XAU" in pair or "GBP" in pair else "NORMAL"

    print(f"  Tech bias: {tech_bias} | Confluence: {confluence}/4 | Vol: {volatility} | Pair risk: {pair_risk}")

    transcript    = []
    bull_pos      = ""
    bear_pos      = ""
    bull_score    = 0.0
    bear_score    = 0.0

    gold_note = "GOLD: Only BUY if 3+ signals align. Avoid chasing spikes." if "XAU" in pair else ""
    gbp_note  = "GBP: Need 150+ pip target. Avoid choppy ranges." if "GBP" in pair else ""

    for rnd in range(1, debate_rounds + 1):
        print(f"  Round {rnd}/{debate_rounds}...")

        # ── BULL ─────────────────────────────────────────────────────
        if rnd == 1:
            bull_prompt = (
                f"You are a BULL TRADER. Strongest case to BUY {pair}.\n"
                f"{gold_note}{gbp_note}\n"
                f"ANALYST REPORTS:\n{combined}\n\n{context}\n"
                f"Structure: 1) Primary thesis 2) 3 supporting data points "
                f"3) Profit target+timeframe 4) Risk/reward 5) Confluence check\n"
                f"End with: Conviction: STRONG / MODERATE / WEAK\n"
                f"Max 280 words."
            )
        else:
            bull_prompt = (
                f"You are a BULL TRADER defending BUY on {pair}.\n"
                f"BEAR ARGUED:\n{bear_pos}\n\n"
                f"REPORTS:\n{combined}\n\n{context}\n"
                f"Counter bear's points. Strengthen case. R:R must be 1.5+.\n"
                f"End with: Conviction: STRONG / MODERATE / WEAK\nMax 220 words."
            )

        bull_arg = llm.call(bull_prompt)
        bull_conv, bull_pts = _conviction_score(bull_arg)
        bull_score += bull_pts
        if tech_bias == "BULLISH":
            bull_score += 0.5

        # ── BEAR ─────────────────────────────────────────────────────
        if rnd == 1:
            bear_prompt = (
                f"You are a BEAR TRADER. Strongest case to SELL {pair}.\n"
                f"{gold_note}{gbp_note}\n"
                f"ANALYST REPORTS:\n{combined}\n\nBULL ARGUED:\n{bull_arg}\n\n{context}\n"
                f"Structure: 1) Primary bearish thesis 2) 3 data points countering bull "
                f"3) Downside target+timeframe 4) Risk/reward 5) Confluence check\n"
                f"End with: Conviction: STRONG / MODERATE / WEAK\n"
                f"Max 280 words."
            )
        else:
            bear_prompt = (
                f"You are a BEAR TRADER defending SELL on {pair}.\n"
                f"BULL DEFENDED:\n{bull_arg}\n\n"
                f"REPORTS:\n{combined}\n\n{context}\n"
                f"Rebut bull. Reinforce bearish case. R:R must be 1.5+.\n"
                f"End with: Conviction: STRONG / MODERATE / WEAK\nMax 220 words."
            )

        bear_arg = llm.call(bear_prompt)
        bear_conv, bear_pts = _conviction_score(bear_arg)
        bear_score += bear_pts
        if tech_bias == "BEARISH":
            bear_score += 0.5

        transcript.append({
            "round": rnd,
            "bull_argument":   bull_arg,
            "bear_argument":   bear_arg,
            "bull_conviction": bull_conv,
            "bear_conviction": bear_conv,
            "bull_score_round": bull_pts,
            "bear_score_round": bear_pts,
        })
        bull_pos = bull_arg
        bear_pos = bear_arg

        print(f"  Round {rnd} done — Bull:{bull_conv}({bull_pts}) Bear:{bear_conv}({bear_pts}) | Total {bull_score:.1f}:{bear_score:.1f}")

    # ── Final lean ────────────────────────────────────────────────────
    if bull_score > bear_score:
        lean       = "BULLISH"
        diff       = bull_score - bear_score
        confidence = min(85, 55 + int(diff * 6))
        if tech_bias == "BULLISH":
            confidence = min(85, confidence + 5)
            print(f"  Tech bias ALIGNS with BULLISH ({confluence}/4 signals)")
        elif tech_bias == "BEARISH":
            confidence = max(55, confidence - 10)
            print(f"  Tech bias CONTRADICTS — reducing confidence")
    elif bear_score > bull_score:
        lean       = "BEARISH"
        diff       = bear_score - bull_score
        confidence = min(85, 55 + int(diff * 6))
        if tech_bias == "BEARISH":
            confidence = min(85, confidence + 5)
            print(f"  Tech bias ALIGNS with BEARISH ({confluence}/4 signals)")
        elif tech_bias == "BULLISH":
            confidence = max(55, confidence - 10)
            print(f"  Tech bias CONTRADICTS — reducing confidence")
    else:
        lean       = "NEUTRAL"
        confidence = 50

    # Pair-specific adjustment
    if pair_risk == "HIGH" and lean != "NEUTRAL":
        if "XAU" in pair:
            confidence = min(85, confidence + 3)
        elif "GBP" in pair and confidence < 65:
            confidence = max(50, confidence - 5)

    # Volatility adjustment
    if volatility == "HIGH":
        confidence = max(50, confidence - 5)
        print(f"  HIGH volatility — confidence reduced by 5%")

    print(f"  FINAL: {lean} ({confidence}%) | Bull:{bull_score:.1f} Bear:{bear_score:.1f}")

    return {
        "transcript":        transcript,
        "lean":              lean,
        "confidence":        confidence,
        "bull_score":        bull_score,
        "bear_score":        bear_score,
        "rounds":            debate_rounds,
        "technical_bias":    tech_bias,
        "confluence_level":  confluence,
        "market_volatility": volatility,
        "pair_specific_risk": pair_risk,
    }
