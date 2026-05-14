from datetime import datetime, time
import logging
from typing import Dict, List
import MetaTrader5 as mt5

logger = logging.getLogger(__name__)

class TrailingStopManager:
    """
    ATR-based dynamic trailing stops that adapt to market volatility.
    Replaces fixed 20-pip trailing with volatility-adjusted levels.
    """
    
    def __init__(self, atr_period: int = 14, atr_multiplier: float = 1.5):
        self.atr_period = atr_period
        self.atr_multiplier = atr_multiplier  # Trail = 1.5 x ATR
    
    def update_trailing_stop(self, symbol: str, current_price: float, 
                            position_type: str, entry_price: float) -> Dict:
        """
        Calculate ATR-based trailing stop level.
        
        Args:
            symbol: Trading pair
            current_price: Current market price
            position_type: "BUY" or "SELL"
            entry_price: Position entry price
        
        Returns:
            {
                "trailing_stop": price,
                "trail_distance_pips": float,
                "atr": float,
                "unrealized_profit_pips": float,
                "status": "active" | "trailing" | "hit"
            }
        """
        
        try:
            # Calculate ATR
            atr = self._get_atr(symbol, self.atr_period)
            
            if atr is None:
                logger.warning(f"Could not calculate ATR for {symbol}. Using fixed 20-pip trail.")
                return self._get_fixed_trailing_stop(symbol, current_price, position_type, entry_price)
            
            # Trail distance = ATR multiplier
            trail_distance = atr * self.atr_multiplier
            trail_pips = trail_distance * 10000
            
            if position_type == "BUY":
                trailing_stop = current_price - trail_distance
                profit_pips = (current_price - entry_price) * 10000
                status = "trailing" if profit_pips > 0 else "active"
            else:  # SELL
                trailing_stop = current_price + trail_distance
                profit_pips = (entry_price - current_price) * 10000
                status = "trailing" if profit_pips > 0 else "active"
            
            result = {
                "trailing_stop": round(trailing_stop, 5),
                "trail_distance_pips": round(trail_pips, 1),
                "atr": round(atr, 5),
                "unrealized_profit_pips": round(profit_pips, 1),
                "status": status,
                "method": "ATR-based"
            }
            
            logger.info(f"{symbol} {position_type}: Trail {result['trail_distance_pips']}pips, "
                       f"SL level: {result['trailing_stop']}, Profit: {profit_pips:.1f}pips")
            return result
        
        except Exception as e:
            logger.error(f"Error updating trailing stop: {e}")
            return self._get_fixed_trailing_stop(symbol, current_price, position_type, entry_price)
    
    def _get_atr(self, symbol: str, period: int) -> float:
        """
        Calculate Average True Range from recent candles.
        """
        try:
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, period + 5)
            
            if rates is None or len(rates) < period:
                logger.warning(f"Insufficient data for ATR: {len(rates) if rates else 0} candles")
                return None
            
            tr_values = []
            for i in range(1, len(rates)):
                high = rates[i]['high']
                low = rates[i]['low']
                close_prev = rates[i-1]['close']
                
                tr = max(
                    high - low,
                    abs(high - close_prev),
                    abs(low - close_prev)
                )
                tr_values.append(tr)
            
            atr = sum(tr_values[-period:]) / period if tr_values else 0
            return atr
        
        except Exception as e:
            logger.error(f"Error calculating ATR for {symbol}: {e}")
            return None
    
    def _get_fixed_trailing_stop(self, symbol: str, current_price: float,
                                position_type: str, entry_price: float) -> Dict:
        """
        Fallback to fixed 20-pip trailing stop.
        """
        fixed_trail = 0.002 if "JPY" not in symbol else 0.2
        
        if position_type == "BUY":
            trailing_stop = current_price - fixed_trail
            profit_pips = (current_price - entry_price) * 10000
        else:
            trailing_stop = current_price + fixed_trail
            profit_pips = (entry_price - current_price) * 10000
        
        return {
            "trailing_stop": round(trailing_stop, 5),
            "trail_distance_pips": 20.0,
            "atr": 0,
            "unrealized_profit_pips": round(profit_pips, 1),
            "status": "trailing" if profit_pips > 0 else "active",
            "method": "Fixed (ATR unavailable)"
        }
    
    def batch_update_positions(self, positions: List[Dict]) -> List[Dict]:
        """
        Update trailing stops for multiple positions.
        
        Args:
            positions: List of {symbol, type, entry_price, current_price}
        
        Returns:
            Updated positions with new trailing stop levels
        """
        updated = []
        for pos in positions:
            result = self.update_trailing_stop(
                pos["symbol"],
                pos["current_price"],
                pos["type"],
                pos["entry_price"]
            )
            pos["trailing_stop"] = result["trailing_stop"]
            updated.append(pos)
        
        return updated
