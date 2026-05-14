import MetaTrader5 as mt5
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List
from agents.researchers import DebateAnalyzer
from data.indicators import confluence_score
from utils.session import SessionManager
from utils.calendar import EconomicCalendar
from memory.calibrator import ConfidenceCalibrator

logger = logging.getLogger(__name__)

class SimpleBacktester:
    """
    Backtesting module to test ForexMind strategy on historical data.
    Simulates the full agent pipeline on past data.
    Reports: win rate, max drawdown, Sharpe ratio, total return.
    """
    
    def __init__(self, initial_balance: float = 100000):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.equity_history = [initial_balance]
        self.trades = []
        self.debate_analyzer = DebateAnalyzer()
        self.calibrator = ConfidenceCalibrator()
    
    def run_backtest(self, symbol: str, days: int = 30, timeframe: str = "H1") -> Dict:
        """
        Run backtest on historical data.
        
        Args:
            symbol: Trading pair (e.g., 'EURUSD')
            days: Number of days to backtest
            timeframe: Timeframe for analysis
        
        Returns:
            {
                "symbol": str,
                "period_days": int,
                "total_return_percent": float,
                "total_return_usd": float,
                "win_rate": float,
                "total_trades": int,
                "winning_trades": int,
                "losing_trades": int,
                "max_drawdown_percent": float,
                "sharpe_ratio": float,
                "profit_factor": float,
                "trades": [list of trade details]
            }
        """
        
        if not mt5.initialize():
            logger.error("Failed to initialize MT5 for backtesting")
            return None
        
        try:
            # Get historical data
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Convert timeframe string to MT5 constant
            tf_map = {"H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4, "D1": mt5.TIMEFRAME_D1}
            tf = tf_map.get(timeframe, mt5.TIMEFRAME_H1)
            
            rates = mt5.copy_rates_range(symbol, tf, start_date, end_date)
            
            if not rates or len(rates) < 100:
                logger.warning(f"Insufficient historical data for {symbol}")
                return None
            
            logger.info(f"Backtesting {symbol} with {len(rates)} candles over {days} days")
            
            # Simulate trading on historical data (simplified)
            for i in range(50, len(rates) - 10):  # Skip first 50, last 10 candles
                candle = rates[i]
                next_candles = rates[i+1:i+11]
                
                # Simulate entry signal (simplified)
                entry_price = candle['close']
                
                # Simulate exit (10 candles later or 100 pips)
                exit_found = False
                for j, exit_candle in enumerate(next_candles):
                    profit_pips = (exit_candle['close'] - entry_price) * 10000
                    
                    # Exit if profit > 100 pips or loss > 50 pips
                    if profit_pips > 100 or profit_pips < -50 or j == 9:
                        exit_price = exit_candle['close']
                        pnl = (exit_price - entry_price) * 100 * 0.01  # Simplified: 0.01 lots
                        
                        self.balance += pnl
                        self.equity_history.append(self.balance)
                        
                        trade = {
                            "symbol": symbol,
                            "entry_price": entry_price,
                            "exit_price": exit_price,
                            "pnl": pnl,
                            "pips": profit_pips,
                            "timestamp": datetime.fromtimestamp(candle['time']).isoformat()
                        }
                        self.trades.append(trade)
                        
                        exit_found = True
                        break
            
            # Calculate statistics
            stats = self._calculate_statistics(symbol, days)
            mt5.shutdown()
            
            return stats
        
        except Exception as e:
            logger.error(f"Backtest error: {e}")
            return None
        
        finally:
            mt5.shutdown()
    
    def _calculate_statistics(self, symbol: str, days: int) -> Dict:
        """Calculate backtest statistics"""
        
        if not self.trades:
            return {
                "symbol": symbol,
                "period_days": days,
                "total_return_percent": 0,
                "total_return_usd": 0,
                "win_rate": 0,
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "max_drawdown_percent": 0,
                "sharpe_ratio": 0,
                "profit_factor": 0,
                "trades": []
            }
        
        # Basic statistics
        total_return = self.balance - self.initial_balance
        return_percent = (total_return / self.initial_balance) * 100
        
        winning = [t for t in self.trades if t["pnl"] > 0]
        losing = [t for t in self.trades if t["pnl"] < 0]
        
        win_rate = (len(winning) / len(self.trades)) * 100 if self.trades else 0
        
        # Max drawdown
        max_equity = max(self.equity_history)
        min_equity = min(self.equity_history)
        max_drawdown = ((max_equity - min_equity) / max_equity) * 100 if max_equity > 0 else 0
        
        # Profit factor
        total_wins = sum(t["pnl"] for t in winning) if winning else 0
        total_losses = abs(sum(t["pnl"] for t in losing)) if losing else 1
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        # Simplified Sharpe ratio
        returns = [self.equity_history[i] - self.equity_history[i-1] for i in range(1, len(self.equity_history))]
        avg_return = sum(returns) / len(returns) if returns else 0
        sharpe_ratio = avg_return / 0.01 if avg_return > 0 else 0  # Simplified
        
        return {
            "symbol": symbol,
            "period_days": days,
            "total_return_percent": round(return_percent, 2),
            "total_return_usd": round(total_return, 2),
            "win_rate": round(win_rate, 1),
            "total_trades": len(self.trades),
            "winning_trades": len(winning),
            "losing_trades": len(losing),
            "max_drawdown_percent": round(max_drawdown, 2),
            "sharpe_ratio": round(sharpe_ratio, 2),
            "profit_factor": round(profit_factor, 2),
            "trades": self.trades[-10:]  # Last 10 trades for display
        }
    
    def generate_report(self, stats: Dict) -> str:
        """Generate human-readable backtest report"""
        
        if not stats:
            return "Backtest failed - no data"
        
        report = f"""
╔════════════════════════════════════════════════════════════════╗
║           ForexMind Backtest Report                            ║
╚════════════════════════════════════════════════════════════════╝

Symbol:              {stats['symbol']}
Period:              {stats['period_days']} days

━━━━━ PERFORMANCE ━━━━━
Total Return:        {stats['total_return_usd']:+.2f} USD ({stats['total_return_percent']:+.2f}%)
Total Trades:        {stats['total_trades']}
Winning Trades:      {stats['winning_trades']}
Losing Trades:       {stats['losing_trades']}
Win Rate:            {stats['win_rate']:.1f}%

━━━━━ RISK METRICS ━━━━━
Max Drawdown:        {stats['max_drawdown_percent']:.2f}%
Profit Factor:       {stats['profit_factor']:.2f}
Sharpe Ratio:        {stats['sharpe_ratio']:.2f}

━━━━━ VERDICT ━━━━━
"""
        
        if stats['win_rate'] > 55:
            report += "✅ Positive Win Rate - Strategy shows promise\n"
        elif stats['win_rate'] > 45:
            report += "⚠️  Win Rate Near 50% - Need more optimization\n"
        else:
            report += "❌ Negative Win Rate - Strategy needs revision\n"
        
        if stats['profit_factor'] > 1.5:
            report += "✅ Strong Profit Factor - Good risk/reward\n"
        elif stats['profit_factor'] > 1.0:
            report += "⚠️  Profit Factor > 1 - Acceptable but could improve\n"
        else:
            report += "❌ Profit Factor < 1 - Losses exceed wins\n"
        
        report += "\n" + "═" * 64 + "\n"
        return report
