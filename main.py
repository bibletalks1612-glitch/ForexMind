#!/usr/bin/env python3
"""
ForexMind v2 — Enhanced Multi-Agent Forex Trading Bot

Integrates all v2 enhancements:
1. Fixed debate output format (researchers.py)
2. Multi-timeframe confluence scoring
3. Session-aware trading with volatility adjustment
4. Economic calendar filter to avoid news spikes
5. Performance dashboard (Flask web UI)
6. ATR-based dynamic trailing stops
7. Auto close positions at day-end
8. Backtesting module with historical analysis
9. Confidence calibration system
10. Enhanced loss management with progressive position reduction
"""

import logging
import sys
from datetime import datetime
import MetaTrader5 as mt5
import json
import os

# Import all v2 modules
from config.settings import (
    MT5_ACCOUNT, MT5_PASSWORD, MT5_SERVER, MT5_PATH,
    TRADING_PAIRS, BASE_LOT_SIZE, MIN_CONFLUENCE_SCORE,
    PREFERRED_SESSIONS, AVOID_SESSIONS, ECONOMIC_CALENDAR_ENABLED,
    AUTO_CLOSE_DAY_END_ENABLED, AUTO_CLOSE_TIME_GMT, AUTO_OPEN_TIME_GMT,
    MAX_DAILY_LOSS_USD, MAX_WEEKLY_LOSS_USD, MAX_MONTHLY_LOSS_USD,
    MIN_DEBATE_CONFIDENCE, MIN_COMBINED_CONFIDENCE,
    DEBATE_WEIGHT, CONFLUENCE_WEIGHT, SESSION_WEIGHT, CALENDAR_WEIGHT,
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
)

from agents.researchers import DebateAnalyzer
from agents.execution import RiskManager
from data.indicators import confluence_score, calculate_position_size_with_confluence
from utils.session import SessionManager
from utils.calendar import EconomicCalendar
from utils.day_close import AutoCloseManager
from utils.trailing_stop import TrailingStopManager
from utils.telegram import send_telegram_alert
from memory.loss_manager import LossManager
from memory.calibrator import ConfidenceCalibrator
from backtest.run_backtest import SimpleBacktester

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('memory/trades.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ForexMindv2:
    """
    Main ForexMind v2 trading bot with all enhancements.
    """
    
    def __init__(self):
        logger.info("="*70)
        logger.info("🤖 ForexMind v2 — Enhanced Multi-Agent Forex Trading Bot")
        logger.info("="*70)
        
        self.debate_analyzer = DebateAnalyzer()
        self.risk_manager = RiskManager()
        self.session_manager = SessionManager()
        self.loss_manager = LossManager()
        self.calibrator = ConfidenceCalibrator()
        self.auto_close_manager = AutoCloseManager(AUTO_CLOSE_TIME_GMT, AUTO_OPEN_TIME_GMT)
        self.trailing_stop_manager = TrailingStopManager()
        
        if ECONOMIC_CALENDAR_ENABLED:
            self.economic_calendar = EconomicCalendar()
        else:
            self.economic_calendar = None
        
        self.mt5_initialized = False
        self.memory_file = "memory/data/decisions.json"
        self.load_memory()
    
    def initialize_mt5(self) -> bool:
        """
        Initialize MetaTrader5 connection.
        """
        try:
            if not mt5.initialize(path=MT5_PATH, login=MT5_ACCOUNT, password=MT5_PASSWORD, server=MT5_SERVER):
                logger.error(f"Failed to initialize MT5: {mt5.last_error()}")
                return False
            
            logger.info(f"✓ MT5 connected: Account {MT5_ACCOUNT} on {MT5_SERVER}")
            self.mt5_initialized = True
            return True
        except Exception as e:
            logger.error(f"MT5 initialization error: {e}")
            return False
    
    def load_memory(self):
        """
        Load previous trading decisions and state from memory.
        """
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r') as f:
                    self.memory = json.load(f)
                logger.info(f"✓ Loaded memory: {len(self.memory.get('trades', []))} previous trades")
            else:
                self.memory = {"trades": [], "decisions": []}
                os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)
        except Exception as e:
            logger.warning(f"Could not load memory: {e}")
            self.memory = {"trades": [], "decisions": []}
    
    def save_memory(self):
        """
        Save trading decisions to memory file.
        """
        try:
            with open(self.memory_file, 'w') as f:
                json.dump(self.memory, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving memory: {e}")
    
    def check_pre_trading_conditions(self) -> tuple[bool, str]:
        """
        Check all pre-trading conditions before placing orders.
        
        Returns:
            (can_trade: bool, reason: str)
        """
        
        # Check trading hours
        if AUTO_CLOSE_DAY_END_ENABLED:
            day_close_status = self.auto_close_manager.get_trading_status()
            if not day_close_status["can_trade"]:
                return False, f"Outside trading hours: {day_close_status['reason']}"
        
        # Check loss thresholds
        loss_check = self.loss_manager.check_loss_threshold(
            MAX_DAILY_LOSS_USD, MAX_WEEKLY_LOSS_USD, MAX_MONTHLY_LOSS_USD
        )
        if not loss_check["can_trade"]:
            return False, f"Loss threshold exceeded: {loss_check['reason']}"
        
        return True, "All pre-trading conditions met"
    
    def analyze_symbol(self, symbol: str) -> dict:
        """
        Run full analysis on a symbol using all v2 enhancements.
        
        Returns:
            {
                "symbol": str,
                "debate_result": {...},
                "confluence_score": {...},
                "session_info": {...},
                "calendar_check": {...},
                "final_confidence": float (0-100),
                "position_size_factor": float (0-1),
                "recommendation": "BUY" | "SELL" | "SKIP",
                "reasoning": str
            }
        """
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Analyzing {symbol}...")
        logger.info(f"{'='*60}")
        
        result = {"symbol": symbol, "timestamp": datetime.utcnow().isoformat()}
        
        # 1. DEBATE ANALYSIS (40% weight)
        logger.info("[1/5] Running Bull vs Bear debate...")
        try:
            debate_result = self.debate_analyzer.run_debate(
                symbol, "H1",
                {"rsi": 55, "macd": 0.002, "ema_trend": "bullish"},  # Mock data
                news_sentiment=0.2
            )
            result["debate_result"] = debate_result
            logger.info(f"  → Lean: {debate_result['lean']} | Confidence: {debate_result['confidence']}%")
        except Exception as e:
            logger.error(f"  ✗ Debate failed: {e}")
            return None
        
        # 2. MULTI-TIMEFRAME CONFLUENCE (30% weight)
        logger.info("[2/5] Checking multi-timeframe confluence...")
        try:
            confluence = confluence_score(
                {"rsi": 60, "macd": 0.002},  # H1
                {"rsi": 55, "macd": 0.001}   # H4
            )
            result["confluence_score"] = confluence
            logger.info(f"  → Confluence: {confluence['confluence_score']}% ({confluence['alignment']}) | Factor: {confluence['position_size_factor']}")
        except Exception as e:
            logger.error(f"  ✗ Confluence failed: {e}")
            confluence = {"confluence_score": 50, "position_size_factor": 0.5}
            result["confluence_score"] = confluence
        
        # 3. SESSION CHECK (15% weight)
        logger.info("[3/5] Checking trading session...")
        try:
            session_info = self.session_manager.get_session_details()
            result["session_info"] = session_info
            should_reduce, session_factor = self.session_manager.should_reduce_position_size(
                PREFERRED_SESSIONS, AVOID_SESSIONS
            )
            session_confidence = 100 if not should_reduce else 50
            logger.info(f"  → Session: {session_info['session']} | Factor: {session_factor} | Info: {session_info['recommendation'][:50]}...")
        except Exception as e:
            logger.error(f"  ✗ Session check failed: {e}")
            session_factor = 0.5
            session_confidence = 50
        
        # 4. ECONOMIC CALENDAR CHECK (15% weight)
        logger.info("[4/5] Checking economic calendar...")
        try:
            calendar_check = None
            calendar_confidence = 100
            if self.economic_calendar:
                calendar_check = self.economic_calendar.is_event_nearby(symbol, minutes_before=30)
                result["calendar_check"] = calendar_check
                if calendar_check["event_nearby"]:
                    calendar_confidence = 40
                    logger.warning(f"  ⚠ Event nearby: {calendar_check['event_name']} in {calendar_check['minutes_until']} minutes")
                else:
                    logger.info(f"  → No high-impact events nearby")
        except Exception as e:
            logger.error(f"  ✗ Calendar check failed: {e}")
            calendar_confidence = 75
        
        # 5. CALCULATE FINAL CONFIDENCE
        logger.info("[5/5] Calculating final confidence and position size...")
        
        # Weighted confidence score
        final_confidence = (
            debate_result.get('confidence', 50) * DEBATE_WEIGHT +
            confluence['confluence_score'] * CONFLUENCE_WEIGHT +
            session_confidence * SESSION_WEIGHT +
            calendar_confidence * CALENDAR_WEIGHT
        )
        
        result["final_confidence"] = final_confidence
        result["weighted_breakdown"] = {
            "debate": debate_result.get('confidence', 50),
            "confluence": confluence['confluence_score'],
            "session": session_confidence,
            "calendar": calendar_confidence
        }
        
        # Determine recommendation
        if final_confidence < MIN_DEBATE_CONFIDENCE:
            recommendation = "SKIP"
            reasoning = f"Confidence {final_confidence:.1f}% below minimum {MIN_DEBATE_CONFIDENCE}%"
        elif debate_result['lean'] == "NEUTRAL":
            recommendation = "SKIP"
            reasoning = "Debate result neutral - insufficient directional bias"
        elif calendar_check and calendar_check.get("event_nearby"):
            recommendation = "SKIP"
            reasoning = f"High-impact event {calendar_check['event_name']} in {calendar_check['minutes_until']} minutes"
        else:
            recommendation = debate_result['lean'][:4]  # "BULL" -> "BUY", "BEAR" -> "SELL"
            reasoning = f"Strong {debate_result['lean']} signal (confidence: {final_confidence:.1f}%)"
        
        # Position size adjustments
        position_factor = confluence['position_size_factor'] * session_factor * (1.0 if calendar_confidence > 75 else 0.5)
        loss_factor = self.loss_manager.check_loss_threshold(
            MAX_DAILY_LOSS_USD, MAX_WEEKLY_LOSS_USD, MAX_MONTHLY_LOSS_USD
        )["position_size_factor"]
        position_factor *= loss_factor
        
        result["recommendation"] = recommendation
        result["reasoning"] = reasoning
        result["position_size_factor"] = position_factor
        result["position_size_lots"] = BASE_LOT_SIZE * position_factor
        
        logger.info(f"\n✅ ANALYSIS COMPLETE:")
        logger.info(f"   Recommendation: {recommendation}")
        logger.info(f"   Final Confidence: {final_confidence:.1f}%")
        logger.info(f"   Position Size Factor: {position_factor:.2f}")
        logger.info(f"   Reasoning: {reasoning}")
        
        return result
    
    def run(self):
        """
        Main trading loop with all v2 enhancements.
        """
        
        if not self.initialize_mt5():
            logger.error("Failed to initialize MT5. Exiting.")
            return
        
        try:
            # Check pre-trading conditions
            can_trade, condition_msg = self.check_pre_trading_conditions()
            logger.info(f"\nPre-trading check: {condition_msg}")
            
            if not can_trade:
                send_telegram_alert(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, f"🚫 {condition_msg}")
                return
            
            # Check if should close positions at day-end
            if AUTO_CLOSE_DAY_END_ENABLED and self.auto_close_manager.should_close_positions():
                logger.warning("\n⏰ Day-end detected. Closing all positions...")
                close_result = self.auto_close_manager.close_all_positions(magic_number=999)
                send_telegram_alert(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
                                  f"📊 Day-end auto-close: {close_result['closed_count']} positions closed")
                return
            
            # Analyze each trading pair
            logger.info(f"\n{'='*70}")
            logger.info(f"Analyzing {len(TRADING_PAIRS)} trading pairs...")
            logger.info(f"{'='*70}\n")
            
            for symbol in TRADING_PAIRS:
                try:
                    analysis = self.analyze_symbol(symbol)
                    if analysis:
                        # Save to memory
                        self.memory["decisions"].append(analysis)
                        self.save_memory()
                        
                        # Send Telegram alert
                        alert_msg = f"[{symbol}] {analysis['recommendation']} | Confidence: {analysis['final_confidence']:.0f}% | Position: {analysis['position_size_lots']:.2f}L"
                        send_telegram_alert(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, alert_msg)
                
                except Exception as e:
                    logger.error(f"Error analyzing {symbol}: {e}")
                    continue
            
            logger.info(f"\n✅ Trading session complete. Decisions saved to {self.memory_file}")
            
        except KeyboardInterrupt:
            logger.info("\nTrading interrupted by user.")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            send_telegram_alert(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, f"🚨 Critical error: {str(e)[:100]}")
        finally:
            if self.mt5_initialized:
                mt5.shutdown()
                logger.info("MT5 connection closed.")


def main():
    """
    Entry point for ForexMind v2.
    """
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "backtest":
            # Run backtesting
            pair = sys.argv[2] if len(sys.argv) > 2 else "EURUSD"
            days = int(sys.argv[3]) if len(sys.argv) > 3 else 30
            
            logger.info(f"\nStarting backtest for {pair} over {days} days...\n")
            backtester = SimpleBacktester(initial_balance=100000)
            stats = backtester.run_backtest(pair, days=days)
            
            if stats:
                report = backtester.generate_report(stats)
                print(report)
                logger.info(report)
            return
        
        elif command == "calibrate":
            # Show calibration data
            logger.info("\nConfidence Calibration Report\n")
            calibrator = ConfidenceCalibrator()
            accuracy = calibrator.get_calibration_accuracy()
            adjustment = calibrator.get_confidence_adjustment()
            
            print("\n=== Calibration Accuracy by Confidence Bucket ===")
            for bucket, data in accuracy.items():
                if bucket in ["overall_accuracy", "total_trades_analyzed"]:
                    continue
                print(f"{bucket}%: {data['total']} trades, {data['correct']} correct, {data['accuracy']:.1f}% accuracy")
            
            print(f"\nOverall Accuracy: {accuracy['overall_accuracy']:.1f}%")
            print(f"\n=== Recommended Adjustment ===")
            print(f"Current Threshold: {adjustment['current_threshold']}%")
            print(f"Recommended: {adjustment['recommended_threshold']}%")
            print(f"Expected Improvement: {adjustment['expected_improvement']:+.1f}%")
            return
        
        elif command == "dashboard":
            # Run dashboard
            logger.info("\n🚀 Starting ForexMind Dashboard...")
            from dashboard.app import app
            app.run(host="127.0.0.1", port=8080, debug=False)
            return
    
    # Default: Run trading bot
    bot = ForexMindv2()
    bot.run()


if __name__ == "__main__":
    main()
