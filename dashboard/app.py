"""
ForexMind - Performance Dashboard (ENHANCEMENT 6)
Web-based dashboard for monitoring trading activity.
Run: pip install flask
     python dashboard/app.py
Access: http://localhost:8080
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from flask import Flask, render_template_string, jsonify
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    print("ERROR: Flask not installed. Run: pip install flask")
    sys.exit(1)

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False


app = Flask(__name__)
MEMORY_DIR = Path("../memory/data")


def get_account_summary() -> dict:
    """Get MT5 account summary."""
    if not MT5_AVAILABLE:
        return {
            "balance": 0,
            "equity": 0,
            "open_pnl": 0,
            "positions": 0
        }
    
    try:
        if not mt5.initialize():
            return {"error": "MT5 not available"}
        
        info = mt5.account_info()
        if info is None:
            return {"error": "Cannot get account info"}
        
        positions = mt5.positions_get(comment="ForexMind AI")
        
        return {
            "balance": round(info.balance, 2),
            "equity": round(info.equity, 2),
            "open_pnl": round(info.equity - info.balance, 2),
            "positions": len(positions) if positions else 0,
            "free_margin": round(info.margin_free, 2)
        }
    except Exception as e:
        return {"error": str(e)}


def get_trade_history() -> list:
    """Get recent trades from memory."""
    try:
        history_file = MEMORY_DIR / "trade_history.json"
        if history_file.exists():
            with open(history_file) as f:
                history = json.load(f)
                return history[-10:]  # Last 10 trades
    except:
        pass
    return []


def get_recent_signals() -> list:
    """Get recent trading signals from decisions."""
    try:
        decisions_file = MEMORY_DIR / "decisions.json"
        if decisions_file.exists():
            with open(decisions_file) as f:
                decisions = json.load(f)
                signals = []
                for pair, data in decisions.items():
                    if isinstance(data, list) and len(data) > 0:
                        latest = data[-1]
                        signals.append({
                            "pair": pair,
                            "action": latest.get("action", "N/A"),
                            "confidence": latest.get("confidence", 0),
                            "time": latest.get("timestamp", "N/A")
                        })
                return signals[-10:]  # Last 10 signals
    except:
        pass
    return []


def get_open_positions() -> list:
    """Get currently open positions."""
    if not MT5_AVAILABLE:
        return []
    
    try:
        if not mt5.initialize():
            return []
        
        positions = mt5.positions_get(comment="ForexMind AI")
        if not positions:
            return []
        
        result = []
        for pos in positions:
            result.append({
                "ticket": pos.ticket,
                "symbol": pos.symbol.replace("USD", "/USD"),
                "type": "BUY" if pos.type == 0 else "SELL",
                "volume": pos.volume,
                "entry": round(pos.price_open, 5),
                "current": round(mt5.symbol_info_tick(pos.symbol).bid 
                               if pos.type == 0 
                               else mt5.symbol_info_tick(pos.symbol).ask, 5),
                "pnl": round(pos.profit, 2),
                "pnl_pct": round((pos.profit / (pos.price_open * pos.volume * 100000)) * 100, 2)
            })
        
        return result
    except:
        return []


# HTML Template
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>ForexMind Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            line-height: 1.6;
        }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            color: white;
        }
        header h1 { font-size: 28px; margin-bottom: 5px; }
        header p { opacity: 0.9; }
        
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 20px; }
        .card {
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 20px;
        }
        .card h3 { color: #94a3b8; font-size: 12px; text-transform: uppercase; margin-bottom: 10px; }
        .card-value { font-size: 24px; font-weight: bold; }
        .positive { color: #10b981; }
        .negative { color: #ef4444; }
        
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }
        table th {
            background: #0f172a;
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #334155;
            color: #94a3b8;
            font-weight: 500;
        }
        table td {
            padding: 12px;
            border-bottom: 1px solid #1e293b;
        }
        table tr:hover { background: rgba(100, 116, 139, 0.1); }
        
        .status-buy { background: rgba(16, 185, 129, 0.1); color: #10b981; }
        .status-sell { background: rgba(239, 68, 68, 0.1); color: #ef4444; }
        
        .refresh { text-align: right; font-size: 12px; color: #64748b; margin-top: 10px; }
        @keyframes spin { to { transform: rotate(360deg); } }
        .loading { display: inline-block; animation: spin 1s linear infinite; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🤖 ForexMind Dashboard</h1>
            <p>Real-time trading monitoring and analytics</p>
        </header>
        
        <div class="grid">
            <div class="card">
                <h3>Account Balance</h3>
                <div class="card-value" id="balance">$0.00</div>
            </div>
            <div class="card">
                <h3>Equity</h3>
                <div class="card-value" id="equity">$0.00</div>
            </div>
            <div class="card">
                <h3>Open P&L</h3>
                <div class="card-value" id="open-pnl">$0.00</div>
            </div>
            <div class="card">
                <h3>Open Positions</h3>
                <div class="card-value" id="positions">0</div>
            </div>
        </div>
        
        <div class="card" style="margin-bottom: 20px;">
            <h3>Open Positions</h3>
            <table id="positions-table">
                <thead>
                    <tr>
                        <th>Pair</th>
                        <th>Type</th>
                        <th>Size</th>
                        <th>Entry</th>
                        <th>Current</th>
                        <th>P&L</th>
                    </tr>
                </thead>
                <tbody id="positions-body">
                    <tr><td colspan="6" style="text-align: center; color: #64748b;">No open positions</td></tr>
                </tbody>
            </table>
            <div class="refresh">Updated <span id="update-time">just now</span></div>
        </div>
        
        <div class="card">
            <h3>Recent Signals</h3>
            <table id="signals-table">
                <thead>
                    <tr>
                        <th>Pair</th>
                        <th>Action</th>
                        <th>Confidence</th>
                        <th>Time</th>
                    </tr>
                </thead>
                <tbody id="signals-body">
                    <tr><td colspan="4" style="text-align: center; color: #64748b;">No signals yet</td></tr>
                </tbody>
            </table>
        </div>
    </div>
    
    <script>
        function updateDashboard() {
            fetch('/api/account')
                .then(r => r.json())
                .then(data => {
                    if (!data.error) {
                        document.getElementById('balance').textContent = '$' + data.balance.toFixed(2);
                        document.getElementById('equity').textContent = '$' + data.equity.toFixed(2);
                        const pnl = data.open_pnl;
                        document.getElementById('open-pnl').textContent = 
                            (pnl >= 0 ? '+' : '') + '$' + pnl.toFixed(2);
                        document.getElementById('positions').textContent = data.positions;
                    }
                });
            
            fetch('/api/positions')
                .then(r => r.json())
                .then(positions => {
                    const tbody = document.getElementById('positions-body');
                    if (positions.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: #64748b;">No open positions</td></tr>';
                    } else {
                        tbody.innerHTML = positions.map(p => `
                            <tr>
                                <td>${p.symbol}</td>
                                <td><span class="status-${p.type.toLowerCase()}">${p.type}</span></td>
                                <td>${p.volume}</td>
                                <td>${p.entry.toFixed(5)}</td>
                                <td>${p.current.toFixed(5)}</td>
                                <td class="${p.pnl >= 0 ? 'positive' : 'negative'}">
                                    ${(p.pnl >= 0 ? '+' : '')}$${p.pnl.toFixed(2)}
                                </td>
                            </tr>
                        `).join('');
                    }
                });
            
            fetch('/api/signals')
                .then(r => r.json())
                .then(signals => {
                    const tbody = document.getElementById('signals-body');
                    if (signals.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: #64748b;">No signals yet</td></tr>';
                    } else {
                        tbody.innerHTML = signals.map(s => `
                            <tr>
                                <td>${s.pair}</td>
                                <td><span class="status-${s.action.toLowerCase()}">${s.action}</span></td>
                                <td>${s.confidence}%</td>
                                <td>${s.time}</td>
                            </tr>
                        `).join('');
                    }
                });
            
            document.getElementById('update-time').textContent = new Date().toLocaleTimeString();
        }
        
        updateDashboard();
        setInterval(updateDashboard, 5000); // Refresh every 5 seconds
    </script>
</body>
</html>
"""


@app.route('/')
def dashboard():
    return render_template_string(DASHBOARD_HTML)


@app.route('/api/account')
def api_account():
    return jsonify(get_account_summary())


@app.route('/api/positions')
def api_positions():
    return jsonify(get_open_positions())


@app.route('/api/signals')
def api_signals():
    return jsonify(get_recent_signals())


@app.route('/api/trades')
def api_trades():
    return jsonify(get_trade_history())


if __name__ == '__main__':
    print("""
    ╔════════════════════════════════════════╗
    ║   ForexMind Dashboard (ENHANCEMENT 6)  ║
    ║   Running on http://localhost:8080     ║
    ║   Press Ctrl+C to stop                 ║
    ╚════════════════════════════════════════╝
    """)
    app.run(host='localhost', port=8080, debug=False)
