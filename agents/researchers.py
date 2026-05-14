import json
from utils.llm import call_llm
from config.settings import GROQ_API_KEY, CEREBRAS_API_KEY, GEMINI_API_KEY

class DebateAnalyzer:
    """Runs Bull vs Bear debate and returns structured lean/confidence output"""
    
    def __init__(self):
        self.bull_analyst = "Bull Market Analyst"
        self.bear_analyst = "Bear Market Analyst"
    
    def run_debate(self, symbol, timeframe, indicators_data, news_sentiment):
        """
        Execute Bull vs Bear debate and return structured result.
        
        Returns:
        {
            "lean": "BULLISH" | "BEARISH" | "NEUTRAL",
            "confidence": 0-100,
            "transcript": [list of round dicts]
        }
        """
        transcript = []
        rounds = 3
        bull_points = 0
        bear_points = 0
        
        # Round 1: Opening arguments
        bull_arg = self._get_bull_argument(symbol, timeframe, indicators_data, round=1)
        bear_arg = self._get_bear_argument(symbol, timeframe, indicators_data, round=1)
        
        bull_strength = self._score_argument(bull_arg)
        bear_strength = self._score_argument(bear_arg)
        
        transcript.append({
            "round": 1,
            "bull": {"argument": bull_arg, "strength": bull_strength},
            "bear": {"argument": bear_arg, "strength": bear_strength}
        })
        
        bull_points += bull_strength
        bear_points += bear_strength
        
        # Round 2: Counter arguments
        bull_counter = self._get_bull_counter(symbol, bear_arg, round=2)
        bear_counter = self._get_bear_counter(symbol, bull_arg, round=2)
        
        bull_counter_strength = self._score_argument(bull_counter)
        bear_counter_strength = self._score_argument(bear_counter)
        
        transcript.append({
            "round": 2,
            "bull": {"argument": bull_counter, "strength": bull_counter_strength},
            "bear": {"argument": bear_counter, "strength": bear_counter_strength}
        })
        
        bull_points += bull_counter_strength
        bear_points += bear_counter_strength
        
        # Round 3: News sentiment influence
        if news_sentiment > 0.3:
            bull_points += 1.5
        elif news_sentiment < -0.3:
            bear_points += 1.5
        
        transcript.append({
            "round": 3,
            "news_sentiment": news_sentiment,
            "impact": "bullish" if news_sentiment > 0.3 else ("bearish" if news_sentiment < -0.3 else "neutral")
        })
        
        # Determine lean and confidence
        total_points = bull_points + bear_points
        
        if total_points == 0:
            lean = "NEUTRAL"
            confidence = 50
        else:
            bull_percentage = (bull_points / total_points) * 100
            bear_percentage = (bear_points / total_points) * 100
            
            # Determine lean
            if bull_percentage > 60:
                lean = "BULLISH"
                confidence = min(int(bull_percentage), 95)
            elif bear_percentage > 60:
                lean = "BEARISH"
                confidence = min(int(bear_percentage), 95)
            else:
                lean = "NEUTRAL"
                confidence = 50
        
        return {
            "lean": lean,
            "confidence": confidence,
            "transcript": transcript,
            "bull_score": bull_points,
            "bear_score": bear_points
        }
    
    def _get_bull_argument(self, symbol, timeframe, indicators_data, round=1):
        """Generate bull market argument using LLM"""
        prompt = f"""
        As a bullish forex analyst for {symbol} on {timeframe} timeframe:
        Current indicators: {json.dumps(indicators_data, indent=2)}
        
        Give ONE strong bullish argument in 1-2 sentences. Focus on momentum, support levels, or trend strength.
        """
        return call_llm(prompt, provider="groq")
    
    def _get_bear_argument(self, symbol, timeframe, indicators_data, round=1):
        """Generate bear market argument using LLM"""
        prompt = f"""
        As a bearish forex analyst for {symbol} on {timeframe} timeframe:
        Current indicators: {json.dumps(indicators_data, indent=2)}
        
        Give ONE strong bearish argument in 1-2 sentences. Focus on resistance, overbought conditions, or downtrend.
        """
        return call_llm(prompt, provider="cerebras")
    
    def _get_bull_counter(self, symbol, bear_arg, round=2):
        """Bull's counter to bear argument"""
        prompt = f"Counter the bear's argument: {bear_arg}\nIn 1 sentence, explain why the bull case still holds."
        return call_llm(prompt, provider="groq")
    
    def _get_bear_counter(self, symbol, bull_arg, round=2):
        """Bear's counter to bull argument"""
        prompt = f"Counter the bull's argument: {bull_arg}\nIn 1 sentence, explain why the bear case still holds."
        return call_llm(prompt, provider="cerebras")
    
    def _score_argument(self, argument_text):
        """
        Score argument strength from 0-3.
        Uses keyword analysis and LLM to evaluate.
        """
        strong_keywords = ['strong', 'confirmed', 'clear', 'significant', 'momentum', 'breakout', 'support', 'resistance']
        weak_keywords = ['weak', 'uncertain', 'may', 'could', 'possible', 'fragile']
        
        score = 1.0  # base score
        text_lower = argument_text.lower()
        
        for keyword in strong_keywords:
            if keyword in text_lower:
                score += 0.5
        
        for keyword in weak_keywords:
            if keyword in text_lower:
                score -= 0.3
        
        return max(0.5, min(3.0, score))
