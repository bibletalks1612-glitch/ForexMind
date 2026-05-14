from datetime import datetime
import logging
from typing import Dict, Tuple
from config.settings import SESSIONS

logger = logging.getLogger(__name__)

class SessionManager:
    """
    Forex market session detector and position size adjuster.
    Manages trading during London, New York, and Asian sessions.
    """
    
    SESSIONS = {
        "asian": {"start": 22, "end": 8, "volatility": "low"},
        "london": {"start": 8, "end": 16, "volatility": "high"},
        "newyork": {"start": 13, "end": 21, "volatility": "high"},
        "overlap": {"start": 8, "end": 12, "volatility": "very high"}  # London + NY overlap
    }
    
    def __init__(self):
        self.current_session = self.get_current_session()
    
    def get_current_session(self) -> str:
        """
        Determine current forex market session based on UTC time.
        
        Returns:
            Session name: "asian" | "london" | "newyork" | "overlap"
        """
        current_hour = datetime.utcnow().hour
        
        # Check overlap first (8 AM - 12 PM = highest volume)
        if 8 <= current_hour < 12:
            return "overlap"
        
        # London session (8 AM - 4 PM UTC)
        if 8 <= current_hour < 16:
            return "london"
        
        # New York session (1 PM - 9 PM UTC)
        if 13 <= current_hour < 21:
            return "newyork"
        
        # Asian session (10 PM - 8 AM UTC, wraps around midnight)
        if current_hour >= 22 or current_hour < 8:
            return "asian"
        
        return "unknown"
    
    def get_session_details(self) -> Dict:
        """
        Get detailed information about current session.
        
        Returns:
            {
                "session": str,
                "volatility": "low" | "high" | "very high",
                "volume": "low" | "medium" | "high",
                "start_utc": int (hour),
                "end_utc": int (hour),
                "time_until_change": int (minutes),
                "recommendation": str
            }
        """
        
        session = self.get_current_session()
        session_info = self.SESSIONS[session]
        
        now = datetime.utcnow()
        current_hour = now.hour
        current_minute = now.minute
        
        # Calculate time until session change
        if session == "overlap":
            next_hour = 12
        elif session == "london":
            next_hour = 16
        elif session == "newyork":
            next_hour = 21
        else:  # asian
            next_hour = 8
        
        minutes_until_change = (next_hour - current_hour - 1) * 60 + (60 - current_minute)
        if minutes_until_change < 0:
            minutes_until_change += 24 * 60
        
        recommendations = {
            "overlap": "BEST: Highest volume and best signal quality. FULL position size.",
            "london": "GOOD: High volume and volatility. FULL position size.",
            "newyork": "GOOD: High volume and volatility. FULL position size.",
            "asian": "CAUTION: Low volume and thin spreads. 50% position size or SKIP."
        }
        
        return {
            "session": session,
            "volatility": session_info["volatility"],
            "volume": "high" if session != "asian" else "low",
            "start_utc": session_info["start"],
            "end_utc": session_info["end"],
            "time_until_change": minutes_until_change,
            "recommendation": recommendations[session]
        }
    
    def should_reduce_position_size(self, preferred_sessions: list, avoid_sessions: list) -> Tuple[bool, float]:
        """
        Check if position should be reduced based on session settings.
        
        Args:
            preferred_sessions: List of preferred session names
            avoid_sessions: List of sessions to avoid
        
        Returns:
            (should_reduce: bool, position_multiplier: 0.0-1.0)
        """
        
        current = self.get_current_session()
        
        # If in avoid session, don't trade
        if current in avoid_sessions:
            logger.warning(f"Current session ({current}) is in AVOID list. Position multiplier: 0.0")
            return True, 0.0
        
        # If not in preferred session, reduce position
        if current not in preferred_sessions:
            logger.info(f"Current session ({current}) not in preferred list. Reducing position to 50%.")
            return True, 0.5
        
        # In preferred session, full position
        logger.info(f"Current session ({current}) is preferred. Full position size.")
        return False, 1.0
    
    def get_session_statistics(self) -> Dict:
        """
        Get statistics about each trading session.
        Useful for understanding best times to trade.
        """
        return {
            "overlap": {
                "name": "London-New York Overlap",
                "utc_time": "08:00 - 12:00",
                "volatility": "Very High",
                "average_pips_per_hour": 80,
                "recommendation": "PRIME TRADING TIME - Best signals and highest profit potential",
                "best_pairs": ["EURUSD", "GBPUSD", "EURGBP"]
            },
            "london": {
                "name": "London Session",
                "utc_time": "08:00 - 16:00",
                "volatility": "High",
                "average_pips_per_hour": 60,
                "recommendation": "Good trading conditions, solid signal quality",
                "best_pairs": ["EURUSD", "GBPUSD", "EURCHF"]
            },
            "newyork": {
                "name": "New York Session",
                "utc_time": "13:00 - 21:00",
                "volatility": "High",
                "average_pips_per_hour": 70,
                "recommendation": "Strong trading conditions, especially for USD pairs",
                "best_pairs": ["EURUSD", "GBPUSD", "USDJPY"]
            },
            "asian": {
                "name": "Asian Session",
                "utc_time": "22:00 - 08:00 (previous day)",
                "volatility": "Low",
                "average_pips_per_hour": 30,
                "recommendation": "LOW LIQUIDITY - Avoid or reduce position size significantly",
                "best_pairs": ["USDJPY", "AUDUSD"] if any else []
            }
        }
