"""Bounded, real public APIs used by the dynamic AgentGuard demo.

These APIs are intentionally low-impact: they retrieve public information and
do not require credentials or mutate external systems.
"""
import json
import urllib.parse
import urllib.request
import urllib.error


class ToolAPIError(RuntimeError):
    pass


def _get_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "AgentGuard/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
        raise ToolAPIError(f"API request failed: {exc}") from exc


def weather(location: str, forecast_days: int = 1):
    """Real weather lookup using Open-Meteo geocoding + forecast APIs."""
    params = urllib.parse.urlencode({"name": location, "count": 1, "language": "en", "format": "json"})
    geo = _get_json(f"https://geocoding-api.open-meteo.com/v1/search?{params}")
    results = geo.get("results", [])
    if not results:
        raise ToolAPIError(f"Location not found: {location}")
    place = results[0]
    lat, lon = place["latitude"], place["longitude"]
    weather_params = urllib.parse.urlencode({
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,precipitation,rain,weather_code,wind_speed_10m",
        "daily": "precipitation_probability_max,precipitation_sum,weather_code",
        "forecast_days": max(1, min(int(forecast_days), 3)),
        "timezone": "auto",
    })
    data = _get_json(f"https://api.open-meteo.com/v1/forecast?{weather_params}")
    return {
        "source": "Open-Meteo",
        "location": place.get("name"),
        "country": place.get("country"),
        "latitude": lat,
        "longitude": lon,
        "current": data.get("current", {}),
        "daily": data.get("daily", {}),
    }


def currency(base: str, quote: str, amount: float = 1):
    """Real exchange-rate lookup using Frankfurter."""
    base, quote = base.upper(), quote.upper()
    params = urllib.parse.urlencode({"base": base, "symbols": quote})
    data = _get_json(f"https://api.frankfurter.app/latest?{params}")
    rate = data.get("rates", {}).get(quote)
    if rate is None:
        raise ToolAPIError(f"No exchange rate returned for {base}->{quote}")
    return {
        "source": "Frankfurter",
        "base": base,
        "quote": quote,
        "rate": rate,
        "amount": amount,
        "converted": float(amount) * float(rate),
        "date": data.get("date"),
    }


def country(country_name: str):
    """Real public country-information lookup using REST Countries."""
    encoded = urllib.parse.quote(country_name)
    data = _get_json(f"https://restcountries.com/v3.1/name/{encoded}?fields=name,capital,population,region,currencies")
    if not data:
        raise ToolAPIError(f"Country not found: {country_name}")
    item = data[0]
    return {
        "source": "REST Countries",
        "name": item.get("name", {}).get("common"),
        "capital": item.get("capital", []),
        "population": item.get("population"),
        "region": item.get("region"),
        "currencies": item.get("currencies", {}),
    }


def news(query: str = "", limit: int = 5):
    """Real public news-like feed using Hacker News Algolia search."""
    params = urllib.parse.urlencode({"query": query, "tags": "story", "hitsPerPage": max(1, min(int(limit), 10))})
    data = _get_json(f"https://hn.algolia.com/api/v1/search?{params}")
    hits = []
    for hit in data.get("hits", []):
        hits.append({
            "title": hit.get("title"),
            "url": hit.get("url"),
            "points": hit.get("points"),
            "created_at": hit.get("created_at"),
        })
    return {"source": "Hacker News Algolia", "query": query, "hits": hits}


LIVE_TOOL_REGISTRY = {
    "weather": {
        "description": "Get current and short-term weather for a public location.",
        "schema": {"location": "city or place name", "forecast_days": "integer 1-3"},
        "callable": weather,
        "policy": "ALLOW",
        "risk": 5,
    },
    "currency": {
        "description": "Get a current public exchange rate between two currencies.",
        "schema": {"base": "ISO currency code", "quote": "ISO currency code", "amount": "number"},
        "callable": currency,
        "policy": "ALLOW",
        "risk": 5,
    },
    "country": {
        "description": "Look up public country facts such as capital, population and region.",
        "schema": {"country_name": "country name"},
        "callable": country,
        "policy": "ALLOW",
        "risk": 5,
    },
    "news": {
        "description": "Search a public technology/news feed for stories matching a query.",
        "schema": {"query": "search terms", "limit": "integer 1-10"},
        "callable": news,
        "policy": "ALLOW",
        "risk": 10,
    },
}
