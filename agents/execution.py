import MetaTrader5 as mt5
import logging
from datetime import datetime
from data.indicators import confluence_score
from memory.loss_manager import LossManager
from config.settings import (
    ATR_PERIOD, ATR_STOP_LOSS_MULTIPLIER, ATR_TAKE_PROFIT_MULTIPLIER,
    FIXED_STOP_LOSS_PIPS, FIXED_TAKE_PROFIT_PIPS,
    MAX_DAILY_LOSS_USD, MAX_WEEKLY_LOSS_USD, MAX_MONTHLY_LOSS_USD
)

logger = logging.getLogger(__name__)

class RiskManager:
    """
    Enhanced risk management with ATR-based stops, confluence scoring,
    and loss-aware position sizing.
    """
    
    def __init__(self):
        self.loss_manager = LossManager()
    
    def calculate_position_size(self, symbol: str, account_balance: float, risk_percent: float,
                               entry_price: float, stop_loss_pips: float,
                               confluence_factor: float = 1.0, loss_factor: float = 1.0) -> float:
        """
        Calculate position size accounting for multiple risk factors.
        
        Args:
            symbol: Trading pair (e.g., 'EURUSD')
            account_balance: Current account balance in USD
            risk_percent: Risk percentage per trade (e.g., 2.0 for 2%)
            entry_price: Entry price
            stop_loss_pips: Stop loss distance in pips
            confluence_factor: 0.5-1.0 from confluence scoring
            loss_factor: 0.0-1.0 from loss management
        
        Returns:
            Position size in lots
        """
        
        # Base position size from risk calculation
        risk_amount = (account_balance * risk_percent) / 100
        
        # Get pip value for symbol (varies by currency pair)
        pip_value = self._get_pip_value(symbol)
        
        # Calculate base lots
        base_lots = risk_amount / (stop_loss_pips * pip_value)
        
        # Apply confluence factor (from multi-timeframe analysis)
        confluence_adjusted = base_lots * confluence_factor
        
        # Apply loss factor (from loss management)
        final_lots = confluence_adjusted * loss_factor
        
        # Round to broker's minimum lot size (typically 0.01)
        final_lots = max(0.01, round(final_lots, 2))
        
        logger.info(f"Position size: {final_lots} lots (base: {base_lots:.2f}, confluence: {confluence_factor}, loss: {loss_factor})")
        return final_lots
    
    def calculate_atr_based_stops(self, symbol: str, entry_price: float, direction: str) -> Dict:
        """
        Calculate ATR-based stop loss and take profit.
        
        Args:
            symbol: Trading pair
            entry_price: Entry price
            direction: "BUY" or "SELL"
        
        Returns:
            {
                "stop_loss": price,
                "take_profit": price,
                "atr": atr_value,
                "stop_loss_pips": pips,
                "take_profit_pips": pips
            }
        """
        
        try:
            # Get ATR(14) from last 100 H1 candles
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 100)
            if rates is None or len(rates) < ATR_PERIOD:
                logger.warning(f"Insufficient data for ATR calculation. Using fixed stops.")
                return self._get_fixed_stops(entry_price, direction)
            
            # Calculate ATR
            atr = self._calculate_atr(rates, ATR_PERIOD)
            
            # Calculate stops
            if direction == "BUY":
                stop_loss = entry_price - (atr * ATR_STOP_LOSS_MULTIPLIER)
                take_profit = entry_price + (atr * ATR_TAKE_PROFIT_MULTIPLIER)
            else:  # SELL
                stop_loss = entry_price + (atr * ATR_STOP_LOSS_MULTIPLIER)
                take_profit = entry_price - (atr * ATR_TAKE_PROFIT_MULTIPLIER)
            
            sl_pips = abs(entry_price - stop_loss) * 10000
            tp_pips = abs(entry_price - take_profit) * 10000
            
            result = {
                "stop_loss": round(stop_loss, 5),
                "take_profit": round(take_profit, 5),
                "atr": round(atr, 5),
                "stop_loss_pips": round(sl_pips, 1),
                "take_profit_pips": round(tp_pips, 1),
                "method": "ATR-based"
            }
            
            logger.info(f"{symbol} {direction}: SL {result['stop_loss_pips']}pips, TP {result['take_profit_pips']}pips (ATR: {atr:.5f})")
            return result
        
        except Exception as e:
            logger.error(f"Error calculating ATR stops: {e}. Using fixed stops.")
            return self._get_fixed_stops(entry_price, direction)
    
    def _get_fixed_stops(self, entry_price: float, direction: str) -> Dict:
        """Fallback to fixed pip stops"""
        if direction == "BUY":
            stop_loss = entry_price - (FIXED_STOP_LOSS_PIPS / 10000)
            take_profit = entry_price + (FIXED_TAKE_PROFIT_PIPS / 10000)
        else:
            stop_loss = entry_price + (FIXED_STOP_LOSS_PIPS / 10000)
            take_profit = entry_price - (FIXED_TAKE_PROFIT_PIPS / 10000)
        
        return {
            "stop_loss": round(stop_loss, 5),
            "take_profit": round(take_profit, 5),
            "atr": 0,
            "stop_loss_pips": FIXED_STOP_LOSS_PIPS,
            "take_profit_pips": FIXED_TAKE_PROFIT_PIPS,
            "method": "Fixed (ATR unavailable)"
        }
    
    def _calculate_atr(self, rates: list, period: int) -> float:
        """Calculate Average True Range"""
        tr_list = []
        for i in range(1, len(rates)):
            high = rates[i]['high']
            low = rates[i]['low']
            close_prev = rates[i-1]['close']
            
            tr = max(
                high - low,
                abs(high - close_prev),
                abs(low - close_prev)
            )
            tr_list.append(tr)
        
        if len(tr_list) < period:
            return sum(tr_list) / len(tr_list) if tr_list else 0
        
        atr = sum(tr_list[-period:]) / period
        return atr
    
    def _get_pip_value(self, symbol: str) -> float:
        """
        Get pip value for a currency pair.
        Varies by pair (e.g., USD pairs vs JPY pairs).
        """
        # JPY pairs have 2 decimal places, others have 4
        if "JPY" in symbol:
            return 0.01
        return 0.0001
    
    def check_total_risk(self, symbol: str, lots: float, stop_loss: float, entry_price: float) -> Dict:
        """
        Check if total risk is acceptable based on loss thresholds.
        """
        pip_value = self._get_pip_value(symbol)
        sl_pips = abs(entry_price - stop_loss) * 10000
        risk_usd = lots * sl_pips * pip_value * 100
        
        loss_check = self.loss_manager.check_loss_threshold(
            MAX_DAILY_LOSS_USD,
            MAX_WEEKLY_LOSS_USD,
            MAX_MONTHLY_LOSS_USD
        )
        
        return {
            "risk_usd": risk_usd,
            "position_factor": loss_check["position_size_factor"],
            "can_trade": loss_check["can_trade"],
            "loss_state": loss_check["loss_state"],
            "warning": loss_check["reason"]
        }
