import json
import logging
from datetime import datetime
from typing import Dict, List
import os

logger = logging.getLogger(__name__)

class ConfidenceCalibrator:
    """
    Calibrates AI confidence predictions against actual trading outcomes.
    Adjusts confidence thresholds based on historical accuracy.
    """
    
    def __init__(self, lookback_trades: int = 20, calibration_file: str = "memory/calibration.json"):
        self.lookback_trades = lookback_trades
        self.calibration_file = calibration_file
        self.confidence_buckets = {
            "50-60": [],
            "60-70": [],
            "70-80": [],
            "80-90": [],
            "90-100": []
        }
        self.load_calibration_data()
    
    def load_calibration_data(self):
        """Load historical calibration data"""
        try:
            if os.path.exists(self.calibration_file):
                with open(self.calibration_file, 'r') as f:
                    data = json.load(f)
                    self.confidence_buckets = data.get("buckets", self.confidence_buckets)
                logger.info(f"Loaded calibration data with {sum(len(v) for v in self.confidence_buckets.values())} records")
        except Exception as e:
            logger.warning(f"Could not load calibration data: {e}")
    
    def record_prediction(self, predicted_confidence: float, actual_outcome: str, symbol: str, pnl: float):
        """
        Record a trade prediction and its actual outcome.
        
        Args:
            predicted_confidence: AI's predicted confidence (0-100)
            actual_outcome: "WIN" or "LOSS"
            symbol: Trading pair
            pnl: Actual P&L from the trade
        """
        
        bucket = self._get_bucket(predicted_confidence)
        
        record = {
            "predicted_confidence": predicted_confidence,
            "actual_outcome": actual_outcome,
            "symbol": symbol,
            "pnl": pnl,
            "timestamp": datetime.utcnow().isoformat(),
            "was_correct": (actual_outcome == "WIN" and predicted_confidence >= 65) or 
                          (actual_outcome == "LOSS" and predicted_confidence < 65)
        }
        
        self.confidence_buckets[bucket].append(record)
        self._save_calibration_data()
        
        logger.info(f"Calibration record: {symbol} @ {predicted_confidence}% confidence = {actual_outcome}")
    
    def get_calibration_accuracy(self) -> Dict:
        """
        Calculate overall calibration accuracy.
        
        Returns:
            {
                "50-60": {"total": int, "correct": int, "accuracy": float},
                "60-70": {...},
                ...,
                "overall_accuracy": float
            }
        """
        
        results = {}
        all_correct = 0
        all_total = 0
        
        for bucket, records in self.confidence_buckets.items():
            if not records:
                results[bucket] = {"total": 0, "correct": 0, "accuracy": 0, "avg_pnl": 0}
                continue
            
            total = len(records)
            correct = sum(1 for r in records if r.get("was_correct"))
            avg_pnl = sum(r.get("pnl", 0) for r in records) / total
            
            accuracy = (correct / total * 100) if total > 0 else 0
            
            results[bucket] = {
                "total": total,
                "correct": correct,
                "accuracy": accuracy,
                "avg_pnl": avg_pnl
            }
            
            all_correct += correct
            all_total += total
        
        overall_accuracy = (all_correct / all_total * 100) if all_total > 0 else 0
        results["overall_accuracy"] = overall_accuracy
        results["total_trades_analyzed"] = all_total
        
        return results
    
    def get_confidence_adjustment(self) -> Dict:
        """
        Get recommended confidence adjustments based on calibration.
        If AI says 70% confidence but only wins 50% of those trades,
        recommend raising threshold to 80%.
        
        Returns:
            {
                "current_threshold": 70,
                "recommended_threshold": 75,
                "adjustment_reason": str,
                "expected_improvement": float (percent)
            }
        """
        
        accuracy = self.get_calibration_accuracy()
        
        if accuracy["total_trades_analyzed"] < self.lookback_trades:
            return {
                "current_threshold": 70,
                "recommended_threshold": 70,
                "adjustment_reason": f"Insufficient data ({accuracy['total_trades_analyzed']}/{self.lookback_trades} trades)",
                "expected_improvement": 0,
                "confidence": "low"
            }
        
        # Find the confidence bucket with best accuracy
        bucket_accuracies = {k: v["accuracy"] for k, v in accuracy.items() if k != "overall_accuracy" and k != "total_trades_analyzed" and v["total"] > 0}
        
        if not bucket_accuracies:
            return {
                "current_threshold": 70,
                "recommended_threshold": 70,
                "adjustment_reason": "No historical data for calibration",
                "expected_improvement": 0,
                "confidence": "low"
            }
        
        best_bucket = max(bucket_accuracies, key=bucket_accuracies.get)
        best_accuracy = bucket_accuracies[best_bucket]
        overall = accuracy["overall_accuracy"]
        
        # Extract lower bound from bucket (e.g., "70-80" -> 70)
        threshold_min = int(best_bucket.split("-")[0])
        threshold_max = int(best_bucket.split("-")[1])
        recommended = (threshold_min + threshold_max) // 2
        
        improvement = best_accuracy - overall
        
        return {
            "current_threshold": 70,
            "recommended_threshold": recommended,
            "adjustment_reason": f"Best performance in {best_bucket}% confidence range ({best_accuracy:.1f}% accuracy)",
            "expected_improvement": improvement,
            "confidence": "high" if accuracy["total_trades_analyzed"] >= 50 else "medium"
        }
    
    def _get_bucket(self, confidence: float) -> str:
        """Determine which confidence bucket a value falls into"""
        if confidence < 60:
            return "50-60"
        elif confidence < 70:
            return "60-70"
        elif confidence < 80:
            return "70-80"
        elif confidence < 90:
            return "80-90"
        else:
            return "90-100"
    
    def _save_calibration_data(self):
        """Save calibration data to file"""
        try:
            os.makedirs(os.path.dirname(self.calibration_file), exist_ok=True)
            with open(self.calibration_file, 'w') as f:
                json.dump({"buckets": self.confidence_buckets}, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving calibration data: {e}")
    
    def get_recent_accuracy(self, limit: int = None) -> float:
        """Get accuracy of last N trades"""
        if limit is None:
            limit = self.lookback_trades
        
        all_records = []
        for records in self.confidence_buckets.values():
            all_records.extend(records)
        
        recent = sorted(all_records, key=lambda x: x["timestamp"], reverse=True)[:limit]
        
        if not recent:
            return 0
        
        correct = sum(1 for r in recent if r["was_correct"])
        return (correct / len(recent) * 100) if recent else 0
