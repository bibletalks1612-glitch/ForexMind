from datetime import datetime, timedelta
import logging
from typing import Dict, List
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class EconomicCalendar:
    """
    Economic calendar filter to avoid trading during high-impact news events.
    Fetches data from Forex Factory or Investing.com.
    """
    
    def __init__(self, source: str = "forexfactory"):
        self.source = source
        self.events = []
        self.fetch_calendar()
    
    def fetch_calendar(self):
        """Fetch this week's high-impact events"""
        try:
            if self.source == "forexfactory":
                self._fetch_forex_factory()
            elif self.source == "investing":
                self._fetch_investing_com()
            logger.info(f"Loaded {len(self.events)} high-impact events from {self.source}")
        except Exception as e:
            logger.error(f"Error fetching economic calendar: {e}")
            self.events = []
    
    def _fetch_forex_factory(self):
        """Scrape Forex Factory calendar"""
        try:
            url = "https://www.forexfactory.com/calendar.php"
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find event rows (simplified parsing)
            rows = soup.find_all('tr', {'class': 'calendar__row'})
            
            for row in rows:
                try:
                    # Extract event details
                    impact = row.find('span', {'class': 'calendar__impact'})
                    event_name = row.find('span', {'class': 'calendar__event-title'})
                    time_td = row.find('td', {'class': 'calendar__time'})
                    
                    if not all([impact, event_name, time_td]):
                        continue
                    
                    impact_level = impact.get('title', 'Low').lower()
                    
                    # Only store high/medium impact events
                    if impact_level not in ['high', 'medium']:
                        continue
                    
                    self.events.append({
                        "time": time_td.text.strip(),
                        "event": event_name.text.strip(),
                        "impact": impact_level,
                        "source": "forexfactory",
                        "timestamp": None  # Will calculate relative to current time
                    })
                except:
                    continue
        except Exception as e:
            logger.error(f"Forex Factory scrape error: {e}")
    
    def _fetch_investing_com(self):
        """Placeholder for Investing.com API"""
        logger.warning("Investing.com integration not yet implemented. Using mock data.")
        # Would use Investing.com API here
        pass
    
    def is_event_nearby(self, symbol: str, minutes_before: int = 30, minutes_after: int = 30) -> Dict:
        """
        Check if a high-impact event is within the specified time window.
        
        Args:
            symbol: Trading pair (e.g., 'EURUSD')
            minutes_before: Minutes before event to avoid
            minutes_after: Minutes after event to avoid
        
        Returns:
            {
                "event_nearby": True/False,
                "event_name": str,
                "event_time": str,
                "minutes_until": int (negative if in past),
                "risk_level": "high" | "medium" | "none"
            }
        """
        
        now = datetime.utcnow()
        base_currency = symbol[:3]
        quote_currency = symbol[3:]
        
        relevant_events = []
        
        for event in self.events:
            # Check if event affects this currency pair
            if base_currency not in event["event"] and quote_currency not in event["event"]:
                continue
            
            # Parse event time (very simplified)
            try:
                event_hour = int(event["time"].split(":")[0])
                event_minute = int(event["time"].split(":")[1])
                event_time = now.replace(hour=event_hour, minute=event_minute, second=0)
                
                # If event time is in the past today, assume it's tomorrow
                if event_time < now:
                    event_time += timedelta(days=1)
                
                minutes_until = int((event_time - now).total_seconds() / 60)
                
                # Check if within avoidance window
                if -minutes_after <= minutes_until <= minutes_before:
                    relevant_events.append({
                        "event_name": event["event"],
                        "event_time": event_time.isoformat(),
                        "minutes_until": minutes_until,
                        "impact": event["impact"]
                    })
            except:
                continue
        
        if relevant_events:
            # Return the closest event
            closest = min(relevant_events, key=lambda x: abs(x["minutes_until"]))
            return {
                "event_nearby": True,
                "event_name": closest["event_name"],
                "event_time": closest["event_time"],
                "minutes_until": closest["minutes_until"],
                "risk_level": "high" if closest["impact"] == "high" else "medium"
            }
        
        return {
            "event_nearby": False,
            "event_name": None,
            "event_time": None,
            "minutes_until": None,
            "risk_level": "none"
        }
    
    def get_events_today(self) -> List[Dict]:
        """Get all events scheduled for today"""
        return [e for e in self.events if e.get("today")]
    
    def get_events_this_week(self) -> List[Dict]:
        """Get all events this week"""
        return self.events
