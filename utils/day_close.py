import logging
from datetime import datetime
from typing import Dict
import MetaTrader5 as mt5
from config.settings import AUTO_CLOSE_TIME_GMT, AUTO_OPEN_TIME_GMT

logger = logging.getLogger(__name__)

class AutoCloseManager:
    """
    Automatic position closing at day-end to avoid overnight swap charges.
    Closes all ForexMind positions at 21:00 GMT (before rollover).
    Resumes trading at 08:30 GMT next morning.
    """
    
    def __init__(self, close_time: str = "21:00", open_time: str = "08:30"):
        """
        Args:
            close_time: Time to close all positions (GMT, HH:MM format)
            open_time: Time to resume trading (GMT, HH:MM format)
        """
        self.close_time = datetime.strptime(close_time, "%H:%M").time()
        self.open_time = datetime.strptime(open_time, "%H:%M").time()
    
    def should_close_positions(self) -> bool:
        """
        Check if it's time to close all positions.
        
        Returns:
            True if current time >= close_time (21:00 GMT)
        """
        current_time = datetime.utcnow().time()
        return current_time >= self.close_time
    
    def should_resume_trading(self) -> bool:
        """
        Check if it's time to resume trading.
        
        Returns:
            True if current time >= open_time (08:30 GMT)
        """
        current_time = datetime.utcnow().time()
        return current_time >= self.open_time
    
    def get_trading_status(self) -> Dict:
        """
        Get current trading status.
        
        Returns:
            {
                "can_trade": True/False,
                "current_time_gmt": str,
                "close_time": str,
                "open_time": str,
                "reason": str,
                "minutes_until_close": int or None
            }
        """
        
        current_dt = datetime.utcnow()
        current_time = current_dt.time()
        
        if current_time >= self.close_time:
            return {
                "can_trade": False,
                "current_time_gmt": current_time.strftime("%H:%M"),
                "close_time": self.close_time.strftime("%H:%M"),
                "open_time": self.open_time.strftime("%H:%M"),
                "reason": "Day-end: All positions should be closed to avoid overnight swap charges.",
                "minutes_until_close": None
            }
        
        if current_time < self.open_time:
            return {
                "can_trade": False,
                "current_time_gmt": current_time.strftime("%H:%M"),
                "close_time": self.close_time.strftime("%H:%M"),
                "open_time": self.open_time.strftime("%H:%M"),
                "reason": "Market closed: Waiting for next trading session (08:30 GMT).",
                "minutes_until_close": None
            }
        
        # Calculate minutes until close
        close_dt = datetime.utcnow().replace(
            hour=self.close_time.hour,
            minute=self.close_time.minute,
            second=0
        )
        minutes_until_close = int((close_dt - current_dt).total_seconds() / 60)
        
        return {
            "can_trade": True,
            "current_time_gmt": current_time.strftime("%H:%M"),
            "close_time": self.close_time.strftime("%H:%M"),
            "open_time": self.open_time.strftime("%H:%M"),
            "reason": "Trading hours active.",
            "minutes_until_close": minutes_until_close
        }
    
    def close_all_positions(self, magic_number: int = 999) -> Dict:
        """
        Close all ForexMind positions (identified by magic number).
        
        Args:
            magic_number: MT5 magic number used to identify ForexMind trades
        
        Returns:
            {
                "closed_count": int,
                "failed_count": int,
                "closed_positions": [list of symbols],
                "message": str
            }
        """
        
        if not mt5.initialize():
            logger.error("Failed to initialize MT5 for auto-close")
            return {
                "closed_count": 0,
                "failed_count": 0,
                "closed_positions": [],
                "message": "MT5 initialization failed"
            }
        
        closed_count = 0
        failed_count = 0
        closed_symbols = []
        
        try:
            positions = mt5.positions_get()
            
            if not positions:
                logger.info("No open positions to close at day-end.")
                return {
                    "closed_count": 0,
                    "failed_count": 0,
                    "closed_positions": [],
                    "message": "No open positions at day-end."
                }
            
            for position in positions:
                # Only close positions with matching magic number
                if position.magic != magic_number:
                    continue
                
                symbol = position.symbol
                
                # Create close request
                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": symbol,
                    "volume": position.volume,
                    "type": mt5.ORDER_TYPE_BUY if position.type == mt5.ORDER_TYPE_SELL else mt5.ORDER_TYPE_SELL,
                    "position": position.ticket,
                    "price": mt5.symbol_info_tick(symbol).ask if position.type == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(symbol).bid,
                    "deviation": 20,
                    "magic": magic_number,
                    "comment": "Day-end auto-close",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_IOC,
                }
                
                result = mt5.order_send(request)
                
                if result.retcode == mt5.TRADE_RETCODE_DONE:
                    closed_count += 1
                    closed_symbols.append(symbol)
                    logger.info(f"Closed {symbol} position at day-end.")
                else:
                    failed_count += 1
                    logger.warning(f"Failed to close {symbol}: {result.comment}")
            
            message = f"Day-end auto-close: {closed_count} positions closed, {failed_count} failed."
            logger.info(message)
            
            return {
                "closed_count": closed_count,
                "failed_count": failed_count,
                "closed_positions": closed_symbols,
                "message": message
            }
        
        except Exception as e:
            logger.error(f"Error closing positions: {e}")
            return {
                "closed_count": closed_count,
                "failed_count": failed_count + 1,
                "closed_positions": closed_symbols,
                "message": f"Error: {str(e)}"
            }
        
        finally:
            mt5.shutdown()
