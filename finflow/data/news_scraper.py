"""
Financial news scraper using Finnhub API.
Fetches market news, sentiment, and economic calendar events.
Falls back to cached data for offline demos.
"""

import json
import os
import time
from datetime import datetime, timedelta

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# Finnhub client — lazy import to avoid issues if not installed
_finnhub_client = None


def _get_client():
    """Get or create Finnhub client."""
    global _finnhub_client
    if _finnhub_client is None:
        import finnhub
        api_key = os.environ.get("FINNHUB_API_KEY", "")
        if not api_key:
            raise RuntimeError(
                "FINNHUB_API_KEY not set. Get a free key at https://finnhub.io/"
            )
        _finnhub_client = finnhub.Client(api_key=api_key)
    return _finnhub_client


def fetch_news(category: str = "forex", min_results: int = 5) -> list[dict]:
    """
    Fetch financial news from Finnhub.
    Returns list of {headline, summary, source, url, datetime, sentiment}.
    """
    cache_file = os.path.join(CACHE_DIR, f"news_{category}.json")

    try:
        client = _get_client()
        raw = client.general_news(category, min_id=0)

        news = []
        for item in raw[:20]:
            news.append({
                "headline": item.get("headline", ""),
                "summary": item.get("summary", ""),
                "source": item.get("source", ""),
                "url": item.get("url", ""),
                "datetime": datetime.fromtimestamp(item.get("datetime", 0)).isoformat(),
                "sentiment": _estimate_sentiment(item.get("headline", "")),
                "category": category,
            })

        if news:
            with open(cache_file, "w") as f:
                json.dump(news, f, indent=2)
            return news

    except Exception:
        pass

    # Fallback to cache
    if os.path.exists(cache_file):
        with open(cache_file) as f:
            return json.load(f)

    # Last resort: return demo headlines
    return _demo_headlines(category)


def fetch_market_sentiment(symbol: str) -> dict:
    """Fetch news sentiment for a specific symbol."""
    cache_file = os.path.join(CACHE_DIR, f"sentiment_{symbol.replace(':', '_')}.json")

    try:
        client = _get_client()
        today = datetime.now().strftime("%Y-%m-%d")
        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        result = client.news_sentiment(symbol)

        sentiment = {
            "symbol": symbol,
            "buzz_articles": result.get("buzz", {}).get("articlesInLastWeek", 0),
            "sentiment_score": result.get("sentiment", {}).get("bearishPercent", 0),
            "bullish_pct": result.get("sentiment", {}).get("bullishPercent", 0),
            "bearish_pct": result.get("sentiment", {}).get("bearishPercent", 0),
            "fetched_at": datetime.now().isoformat(),
        }

        with open(cache_file, "w") as f:
            json.dump(sentiment, f, indent=2)
        return sentiment

    except Exception:
        if os.path.exists(cache_file):
            with open(cache_file) as f:
                return json.load(f)
        return {"symbol": symbol, "sentiment_score": 0.5, "bullish_pct": 50, "bearish_pct": 50}


def fetch_economic_calendar(days_ahead: int = 7) -> list[dict]:
    """Fetch upcoming economic events."""
    cache_file = os.path.join(CACHE_DIR, "economic_calendar.json")

    try:
        client = _get_client()
        today = datetime.now().strftime("%Y-%m-%d")
        end = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        raw = client.economic_calendar(_from=today, to=end)

        events = []
        for item in raw.get("economicCalendar", [])[:20]:
            events.append({
                "event": item.get("event", ""),
                "country": item.get("country", ""),
                "date": item.get("date", ""),
                "impact": item.get("impact", "low"),
                "forecast": item.get("estimate", ""),
                "previous": item.get("prev", ""),
                "actual": item.get("actual", ""),
            })

        if events:
            with open(cache_file, "w") as f:
                json.dump(events, f, indent=2)
            return events

    except Exception:
        pass

    if os.path.exists(cache_file):
        with open(cache_file) as f:
            return json.load(f)

    return _demo_calendar()


def _estimate_sentiment(headline: str) -> str:
    """Simple keyword-based sentiment estimation for demo purposes."""
    headline_lower = headline.lower()
    bearish = ["drop", "fall", "decline", "crash", "fear", "risk", "war",
               "crisis", "recession", "bearish", "plunge", "tumble", "loss"]
    bullish = ["rise", "gain", "rally", "surge", "bullish", "growth",
               "recovery", "strong", "boost", "high", "record", "up"]

    bear_count = sum(1 for w in bearish if w in headline_lower)
    bull_count = sum(1 for w in bullish if w in headline_lower)

    if bear_count > bull_count:
        return "bearish"
    elif bull_count > bear_count:
        return "bullish"
    return "neutral"


def _demo_headlines(category: str) -> list[dict]:
    """Fallback demo headlines when API is unavailable."""
    return [
        {
            "headline": "Strait of Hormuz Disruption Sends Oil Prices Above $110 as Supply Fears Mount",
            "summary": "The continued closure of the Strait of Hormuz following US-Israeli strikes on Iran has pushed Brent crude above $110/barrel.",
            "source": "Reuters",
            "url": "",
            "datetime": datetime.now().isoformat(),
            "sentiment": "bearish",
            "category": category,
        },
        {
            "headline": "Federal Reserve Holds Rates Steady at 3.50-3.75%, Signals One Cut for 2026",
            "summary": "The FOMC voted 11-1 to keep rates unchanged, with Chair Powell striking a hawkish tone on inflation.",
            "source": "CNBC",
            "url": "",
            "datetime": datetime.now().isoformat(),
            "sentiment": "neutral",
            "category": category,
        },
        {
            "headline": "ECB Raises Inflation Forecast to 2.6% Amid Energy Shock, Stagflation Fears Rise",
            "summary": "The European Central Bank held rates at 2.00% but warned of stagflationary risks from the Middle East conflict.",
            "source": "Bloomberg",
            "url": "",
            "datetime": datetime.now().isoformat(),
            "sentiment": "bearish",
            "category": category,
        },
        {
            "headline": "Gold Holds Above $4,400 on Safe-Haven Demand as Geopolitical Risks Persist",
            "summary": "Central bank buying averaging 585 tonnes/quarter supports gold prices near record levels.",
            "source": "Financial Times",
            "url": "",
            "datetime": datetime.now().isoformat(),
            "sentiment": "bullish",
            "category": category,
        },
        {
            "headline": "OPEC+ Agrees to Add 206K b/d in April Despite Strait of Hormuz Crisis",
            "summary": "Saudi Arabia and Russia led the decision to resume unwinding voluntary production cuts.",
            "source": "OilPrice.com",
            "url": "",
            "datetime": datetime.now().isoformat(),
            "sentiment": "bearish",
            "category": category,
        },
    ]


def _demo_calendar() -> list[dict]:
    """Fallback demo economic calendar."""
    base = datetime.now()
    return [
        {"event": "US Core PCE Price Index", "country": "US", "date": (base + timedelta(days=2)).strftime("%Y-%m-%d"), "impact": "high", "forecast": "2.7%", "previous": "2.6%", "actual": ""},
        {"event": "Eurozone CPI Flash Estimate", "country": "EU", "date": (base + timedelta(days=3)).strftime("%Y-%m-%d"), "impact": "high", "forecast": "2.6%", "previous": "2.4%", "actual": ""},
        {"event": "US Non-Farm Payrolls", "country": "US", "date": (base + timedelta(days=5)).strftime("%Y-%m-%d"), "impact": "high", "forecast": "175K", "previous": "151K", "actual": ""},
        {"event": "ECB Monetary Policy Meeting", "country": "EU", "date": (base + timedelta(days=7)).strftime("%Y-%m-%d"), "impact": "high", "forecast": "2.00%", "previous": "2.00%", "actual": ""},
    ]
