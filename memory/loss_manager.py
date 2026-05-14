import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)

class LossManager:
    """
    Enhanced loss handling and risk management.
    Implements progressive position reduction based on daily/weekly/monthly losses.
    """
    
    def __init__(self, memory_file: str = "memory/data/decisions.json"):
        self.memory_file = memory_file
        self.daily_loss = 0.0
        self.weekly_loss = 0.0
        self.monthly_loss = 0.0
        self.loss_state = "normal"  # normal, caution, warning, danger, halt
        self.load_losses_from_memory()
    
    def load_losses_from_memory(self):
        """Load current losses from trading memory"""
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r') as f:
                    data = json.load(f)
                    trades = data.get("trades", [])
                    
                    now = datetime.utcnow()
                    today = now.date()
                    week_start = today - timedelta(days=today.weekday())
                    month_start = today.replace(day=1)
                    
                    for trade in trades:
                        trade_date = datetime.fromisoformat(trade.get("timestamp", "")).date()
                        pnl = trade.get("pnl", 0.0)
                        
                        if trade_date == today:
                            self.daily_loss += pnl
                        if trade_date >= week_start:
                            self.weekly_loss += pnl
                        if trade_date >= month_start:
                            self.monthly_loss += pnl
            
            self._update_loss_state()
        except Exception as e:
            logger.error(f"Error loading losses: {e}")
    
    def check_loss_threshold(self, max_daily_loss: float, max_weekly_loss: float, max_monthly_loss: float) -> Dict:
        """
        Check if losses exceed thresholds and return adjustment factors.
        
        Returns:
            {
                "position_size_factor": 0.0-1.0,
                "can_trade": True/False,
                "loss_state": "normal" | "caution" | "warning" | "danger" | "halt",
                "reason": explanation string
            }
        """
        
        # Check daily loss
        if self.daily_loss <= max_daily_loss:
            return {
                "position_size_factor": 0.0,
                "can_trade": False,
                "loss_state": "halt",
                "reason": f"Daily loss limit reached: ${self.daily_loss:.2f} <= ${max_daily_loss:.2f}"
            }
        
        # Check weekly loss
        if self.weekly_loss <= max_weekly_loss:
            position_factor = 0.25  # 25% position size
            state = "danger"
            reason = f"Weekly loss critical: ${self.weekly_loss:.2f} <= ${max_weekly_loss:.2f}. Position: 25%"
            logger.warning(reason)
            return {
                "position_size_factor": position_factor,
                "can_trade": True,
                "loss_state": state,
                "reason": reason
            }
        
        # Check monthly loss
        if self.monthly_loss <= max_monthly_loss:
            position_factor = 0.5  # 50% position size
            state = "warning"
            reason = f"Monthly loss warning: ${self.monthly_loss:.2f} <= ${max_monthly_loss:.2f}. Position: 50%"
            logger.warning(reason)
            return {
                "position_size_factor": position_factor,
                "can_trade": True,
                "loss_state": state,
                "reason": reason
            }
        
        # Check caution threshold (half of daily max)
        if self.daily_loss <= max_daily_loss * 0.5:
            position_factor = 0.75  # 75% position size
            state = "caution"
            reason = f"Daily loss approaching limit: ${self.daily_loss:.2f}. Position: 75%"
            logger.info(reason)
            return {
                "position_size_factor": position_factor,
                "can_trade": True,
                "loss_state": state,
                "reason": reason
            }
        
        # Normal state
        return {
            "position_size_factor": 1.0,
            "can_trade": True,
            "loss_state": "normal",
            "reason": f"Losses within acceptable range. Daily: ${self.daily_loss:.2f}, Weekly: ${self.weekly_loss:.2f}"
        }
    
    def _update_loss_state(self):
        """Update internal loss state based on current losses"""
        if self.daily_loss <= -2000:
            self.loss_state = "halt"
        elif self.daily_loss <= -1000:
            self.loss_state = "danger"
        elif self.daily_loss <= -500:
            self.loss_state = "warning"
        elif self.daily_loss <= -250:
            self.loss_state = "caution"
        else:
            self.loss_state = "normal"
    
    def record_trade_pnl(self, symbol: str, pnl: float, entry_price: float, exit_price: float, lots: float):
        """Record a closed trade's P&L to memory"""
        try:
            data = {"trades": []}
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r') as f:
                    data = json.load(f)
            
            trade_record = {
                "symbol": symbol,
                "pnl": pnl,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "lots": lots,
                "timestamp": datetime.utcnow().isoformat(),
                "win": "YES" if pnl > 0 else "NO"
            }
            
            data["trades"].append(trade_record)
            
            with open(self.memory_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            # Update totals
            self.daily_loss += pnl
            self.weekly_loss += pnl
            self.monthly_loss += pnl
            self._update_loss_state()
            
            logger.info(f"Trade recorded: {symbol} {'+' if pnl > 0 else ''}{pnl:.2f}. Daily total: {self.daily_loss:.2f}")
        except Exception as e:
            logger.error(f"Error recording trade: {e}")
    
    def get_loss_summary(self) -> Dict:
        """Get current loss summary"""
        return {
            "daily_loss": self.daily_loss,
            "weekly_loss": self.weekly_loss,
            "monthly_loss": self.monthly_loss,
            "loss_state": self.loss_state
        }
    
    def reset_daily_loss(self):
        """Reset daily loss counter (call at start of each trading day)"""
        self.daily_loss = 0.0
        self.loss_state = "normal"
        logger.info("Daily loss counter reset.")
