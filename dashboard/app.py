from flask import Flask, render_template, jsonify
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

MEMORY_FILE = "memory/data/decisions.json"

class DashboardData:
    """Load and process trading data for dashboard display"""
    
    def __init__(self, memory_file: str = MEMORY_FILE):
        self.memory_file = memory_file
        self.data = self._load_data()
    
    def _load_data(self):
        """Load trading decisions from memory"""
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading memory file: {e}")
        return {"trades": [], "decisions": []}
    
    def get_summary(self):
        """Get trading summary statistics"""
        trades = self.data.get("trades", [])
        
        if not trades:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0,
                "total_pnl": 0,
                "average_win": 0,
                "average_loss": 0,
                "profit_factor": 0,
                "largest_win": 0,
                "largest_loss": 0
            }
        
        winning_trades = [t for t in trades if t.get("pnl", 0) > 0]
        losing_trades = [t for t in trades if t.get("pnl", 0) < 0]
        
        total_wins = sum(t.get("pnl", 0) for t in winning_trades)
        total_losses = sum(abs(t.get("pnl", 0)) for t in losing_trades)
        
        return {
            "total_trades": len(trades),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": (len(winning_trades) / len(trades) * 100) if trades else 0,
            "total_pnl": sum(t.get("pnl", 0) for t in trades),
            "average_win": (total_wins / len(winning_trades)) if winning_trades else 0,
            "average_loss": (total_losses / len(losing_trades)) if losing_trades else 0,
            "profit_factor": (total_wins / total_losses) if total_losses > 0 else 0,
            "largest_win": max((t.get("pnl", 0) for t in trades), default=0),
            "largest_loss": min((t.get("pnl", 0) for t in trades), default=0)
        }
    
    def get_pnl_by_symbol(self):
        """Get P&L breakdown by symbol"""
        trades = self.data.get("trades", [])
        by_symbol = defaultdict(lambda: {"trades": 0, "pnl": 0, "wins": 0})
        
        for trade in trades:
            symbol = trade.get("symbol", "UNKNOWN")
            pnl = trade.get("pnl", 0)
            by_symbol[symbol]["trades"] += 1
            by_symbol[symbol]["pnl"] += pnl
            if pnl > 0:
                by_symbol[symbol]["wins"] += 1
        
        return {symbol: {
            **stats,
            "win_rate": (stats["wins"] / stats["trades"] * 100) if stats["trades"] > 0 else 0
        } for symbol, stats in by_symbol.items()}
    
    def get_equity_curve(self):
        """Generate equity curve data for charting"""
        trades = self.data.get("trades", [])
        if not trades:
            return []
        
        # Sort by timestamp
        sorted_trades = sorted(trades, key=lambda x: x.get("timestamp", ""))
        
        equity_curve = []
        running_pnl = 0
        
        for i, trade in enumerate(sorted_trades):
            running_pnl += trade.get("pnl", 0)
            equity_curve.append({
                "trade_number": i + 1,
                "timestamp": trade.get("timestamp", ""),
                "equity": running_pnl,
                "symbol": trade.get("symbol", "")
            })
        
        return equity_curve
    
    def get_recent_trades(self, limit=20):
        """Get most recent trades"""
        trades = self.data.get("trades", [])
        sorted_trades = sorted(trades, key=lambda x: x.get("timestamp", ""), reverse=True)
        return sorted_trades[:limit]
    
    def get_current_positions(self):
        """Get currently open positions (from MT5)"""
        import MetaTrader5 as mt5
        try:
            if not mt5.initialize():
                return []
            
            positions = mt5.positions_get()
            mt5.shutdown()
            
            return [{
                "symbol": pos.symbol,
                "type": "BUY" if pos.type == mt5.ORDER_TYPE_BUY else "SELL",
                "volume": pos.volume,
                "entry_price": pos.price_open,
                "current_price": mt5.symbol_info_tick(pos.symbol).last,
                "profit": pos.profit,
                "profit_pips": (mt5.symbol_info_tick(pos.symbol).last - pos.price_open) * 10000 if pos.type == mt5.ORDER_TYPE_BUY else (pos.price_open - mt5.symbol_info_tick(pos.symbol).last) * 10000
            } for pos in positions] if positions else []
        except:
            return []

# Routes
@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/summary')
def api_summary():
    """Get trading summary"""
    dashboard = DashboardData()
    return jsonify(dashboard.get_summary())

@app.route('/api/pnl-by-symbol')
def api_pnl_by_symbol():
    """Get P&L by symbol"""
    dashboard = DashboardData()
    return jsonify(dashboard.get_pnl_by_symbol())

@app.route('/api/equity-curve')
def api_equity_curve():
    """Get equity curve data"""
    dashboard = DashboardData()
    return jsonify(dashboard.get_equity_curve())

@app.route('/api/recent-trades')
def api_recent_trades():
    """Get recent trades"""
    dashboard = DashboardData()
    return jsonify(dashboard.get_recent_trades())

@app.route('/api/positions')
def api_positions():
    """Get current open positions"""
    dashboard = DashboardData()
    return jsonify(dashboard.get_current_positions())

if __name__ == '__main__':
    import sys
    host = sys.argv[1] if len(sys.argv) > 1 else '127.0.0.1'
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8080
    
    print(f"\n🚀 ForexMind Dashboard starting at http://{host}:{port}")
    print(f"📊 Live trading data: {MEMORY_FILE}")
    print(f"📈 Real-time P&L tracking and position monitoring\n")
    
    app.run(host=host, port=port, debug=False)
