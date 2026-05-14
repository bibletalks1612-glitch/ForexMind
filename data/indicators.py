import json
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

def confluence_score(indicators_h1: Dict, indicators_h4: Dict, indicators_d1: Dict = None) -> Dict:
    """
    Multi-timeframe confluence scoring.
    Checks if H1, H4, and D1 (optional) indicators agree on the same direction.
    
    Args:
        indicators_h1: H1 indicators {rsi, macd, trend, etc}
        indicators_h4: H4 indicators {rsi, macd, trend, etc}
        indicators_d1: D1 indicators (optional)
    
    Returns:
        {
            "confluence_score": 0-100,
            "alignment": "strong" | "moderate" | "weak",
            "h1_bias": "bullish" | "bearish" | "neutral",
            "h4_bias": "bullish" | "bearish" | "neutral",
            "d1_bias": "bullish" | "bearish" | "neutral" (if provided),
            "position_size_factor": 0.5-1.0,  # Risk multiplier
            "confidence_adjustment": -20 to +20  # Confidence modifier
        }
    """
    
    # Get bias from each timeframe
    h1_bias = _get_timeframe_bias(indicators_h1)
    h4_bias = _get_timeframe_bias(indicators_h4)
    d1_bias = _get_timeframe_bias(indicators_d1) if indicators_d1 else None
    
    # Count agreements
    total_frames = 2
    agreements = 0
    
    if h1_bias == h4_bias and h1_bias != "neutral":
        agreements += 2  # Strong agreement
    elif h1_bias == h4_bias:
        agreements += 1  # Weak agreement (both neutral)
    else:
        agreements -= 1  # Disagreement
    
    if indicators_d1:
        total_frames = 3
        if d1_bias == h1_bias == h4_bias and h1_bias != "neutral":
            agreements += 3  # All three agree
        elif d1_bias == h1_bias or d1_bias == h4_bias:
            agreements += 1
        else:
            agreements -= 2  # D1 disagrees with both
    
    # Calculate confluence score (0-100)
    # Perfect agreement = 100
    # Strong disagreement = 0
    max_agreement = 5 if indicators_d1 else 2
    confluence = max(0, min(100, int((agreements / max_agreement) * 100)))
    
    # Determine alignment quality
    if confluence >= 80:
        alignment = "strong"
        position_size_factor = 1.0  # Full position
        confidence_adjustment = +20
    elif confluence >= 60:
        alignment = "moderate"
        position_size_factor = 0.75  # 75% position
        confidence_adjustment = +10
    else:
        alignment = "weak"
        position_size_factor = 0.5  # 50% position (reduced risk)
        confidence_adjustment = -20
    
    result = {
        "confluence_score": confluence,
        "alignment": alignment,
        "h1_bias": h1_bias,
        "h4_bias": h4_bias,
        "position_size_factor": position_size_factor,
        "confidence_adjustment": confidence_adjustment,
        "analysis": f"Confluence {confluence}% - {alignment} alignment. Position size: {position_size_factor*100}%"
    }
    
    if indicators_d1:
        result["d1_bias"] = d1_bias
    
    logger.info(f"Confluence Score: {confluence}% | H1:{h1_bias} H4:{h4_bias} | Factor: {position_size_factor}")
    return result


def _get_timeframe_bias(indicators: Dict) -> str:
    """
    Determine bullish/bearish/neutral bias from indicators.
    
    Scoring:
    - RSI > 60: bullish, RSI < 40: bearish
    - MACD positive: bullish, negative: bearish
    - EMA slope positive: bullish, negative: bearish
    - Support/Resistance breaks: directional
    """
    
    if not indicators:
        return "neutral"
    
    bullish_points = 0
    bearish_points = 0
    total_indicators = 0
    
    # RSI Analysis (30-70 scale)
    if "rsi" in indicators:
        rsi = indicators["rsi"]
        total_indicators += 1
        if rsi > 65:
            bullish_points += 2
        elif rsi > 55:
            bullish_points += 1
        elif rsi < 35:
            bearish_points += 2
        elif rsi < 45:
            bearish_points += 1
    
    # MACD Analysis
    if "macd" in indicators:
        macd = indicators["macd"]
        total_indicators += 1
        if isinstance(macd, dict):
            if macd.get("histogram", 0) > 0:
                bullish_points += 1.5
            elif macd.get("histogram", 0) < 0:
                bearish_points += 1.5
        else:
            if macd > 0:
                bullish_points += 1.5
            else:
                bearish_points += 1.5
    
    # EMA Slope (trend direction)
    if "ema_trend" in indicators:
        trend = indicators["ema_trend"]
        total_indicators += 1
        if trend == "uptrend" or trend == "bullish":
            bullish_points += 2
        elif trend == "downtrend" or trend == "bearish":
            bearish_points += 2
    
    # Support/Resistance Breaks
    if "near_support" in indicators:
        total_indicators += 0.5
        bearish_points += 0.5
    if "near_resistance" in indicators:
        total_indicators += 0.5
        bullish_points += 0.5
    
    # ADX (Trend Strength)
    if "adx" in indicators:
        adx = indicators["adx"]
        total_indicators += 0.5
        if adx > 30:  # Strong trend
            if bullish_points > bearish_points:
                bullish_points += 1
            elif bearish_points > bullish_points:
                bearish_points += 1
    
    # Bollinger Bands Position
    if "bb_position" in indicators:
        bb_pos = indicators["bb_position"]
        total_indicators += 0.5
        if bb_pos == "upper":
            bullish_points += 1
        elif bb_pos == "lower":
            bearish_points += 1
    
    # Determine bias
    if total_indicators == 0:
        return "neutral"
    
    net_score = bullish_points - bearish_points
    strength = abs(net_score) / total_indicators
    
    if net_score > 0:
        return "bullish"
    elif net_score < 0:
        return "bearish"
    else:
        return "neutral"


def calculate_position_size_with_confluence(base_position: float, confluence_factor: float) -> float:
    """
    Adjust position size based on confluence score.
    
    Args:
        base_position: Initial position size in lots
        confluence_factor: 0.5-1.0 from confluence_score()
    
    Returns:
        Adjusted position size in lots
    """
    adjusted = base_position * confluence_factor
    logger.info(f"Position size adjusted: {base_position} → {adjusted} (factor: {confluence_factor})")
    return adjusted
