"""
ROLEX AI — Internet / Live Information
Retrieval-only web capabilities + Open-Meteo weather + OpenWeather fallback.
Network failures degrade gracefully to cached/offline responses.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Dict, List, Optional

from config import CONFIG
from data.database import get_db
from modules.logger import get_logger

log = get_logger("rolex.web")


# ---------------------------------------------------------------------------
# Network manager
# ---------------------------------------------------------------------------
class NetworkManager:
    def __init__(self):
        self.db = get_db()

    def is_online(self, timeout: float = 3.0) -> bool:
        try:
            urllib.request.urlopen("https://api.open-meteo.com", timeout=timeout)
            return True
        except Exception:
            return False

    def fetch_json(self, url: str, headers: Optional[Dict[str, str]] = None,
                   timeout: Optional[float] = None, retries: Optional[int] = None) -> Optional[dict]:
        timeout = timeout or CONFIG.http_timeout
        retries = CONFIG.http_retries if retries is None else retries
        headers = headers or {"User-Agent": "RolexAI/1.0"}
        last_err = None
        for attempt in range(retries + 1):
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    return json.loads(resp.read().decode("utf-8", errors="replace"))
            except Exception as e:
                last_err = e
                if attempt < retries:
                    time.sleep(0.5 * (attempt + 1))
        log.warning("fetch_json failed for %s: %s", url, last_err)
        return None

    def fetch_text(self, url: str, timeout: Optional[float] = None) -> Optional[str]:
        timeout = timeout or CONFIG.http_timeout
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "RolexAI/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            log.warning("fetch_text failed for %s: %s", url, e)
            return None

    # -- cache --------------------------------------------------------------
    def cache_set(self, key: str, value: str, ttl: Optional[float] = None) -> None:
        expires = time.time() + ttl if ttl else None
        self.db.execute(
            "INSERT INTO cache(key, value, expires_at, created_at) VALUES(?,?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, expires_at=excluded.expires_at, "
            "created_at=excluded.created_at",
            (key, value, expires, time.time()),
        )

    def cache_get(self, key: str) -> Optional[str]:
        row = self.db.query_one("SELECT value, expires_at FROM cache WHERE key=?", (key,))
        if not row:
            return None
        if row["expires_at"] and row["expires_at"] < time.time():
            return None
        return row["value"]


# ---------------------------------------------------------------------------
# Weather (Open-Meteo primary, OpenWeather fallback)
# ---------------------------------------------------------------------------
class WeatherService:
    def __init__(self, net: NetworkManager):
        self.net = net

    def geocode(self, location: str) -> Optional[Dict]:
        url = ("https://geocoding-api.open-meteo.com/v1/search?name="
               + urllib.parse.quote(location) + "&count=1&language=en&format=json")
        data = self.net.fetch_json(url)
        if data and data.get("results"):
            r = data["results"][0]
            return {"name": r.get("name"), "lat": r.get("latitude"), "lon": r.get("longitude"),
                    "country": r.get("country")}
        return None

    def get_weather(self, location: Optional[str] = None) -> Dict:
        location = location or CONFIG.default_location
        cache_key = f"weather:{location.lower()}"
        cached = self.net.cache_get(cache_key)

        geo = self.geocode(location)
        if not geo:
            if cached:
                return {"ok": True, "offline": True, "cached": True, "summary": cached}
            return {"ok": False, "error": f"Could not find location: {location}"}

        url = (f"https://api.open-meteo.com/v1/forecast?latitude={geo['lat']}&longitude={geo['lon']}"
               "&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code"
               "&timezone=auto")
        data = self.net.fetch_json(url)
        if not data or "current" not in data:
            if cached:
                return {"ok": True, "offline": True, "cached": True, "summary": cached}
            return {"ok": False, "error": "Weather service unavailable."}

        cur = data["current"]
        code = cur.get("weather_code", 0)
        desc = self._code_to_text(code)
        summary = (f"{geo['name']}: {cur.get('temperature_2m')}°C, {desc}, "
                   f"humidity {cur.get('relative_humidity_2m')}%, "
                   f"wind {cur.get('wind_speed_10m')} km/h")
        self.net.cache_set(cache_key, summary, ttl=1800)
        return {"ok": True, "location": geo["name"], "country": geo.get("country"),
                "temperature": cur.get("temperature_2m"), "humidity": cur.get("relative_humidity_2m"),
                "wind": cur.get("wind_speed_10m"), "code": code, "description": desc,
                "summary": summary}

    @staticmethod
    def _code_to_text(code: int) -> str:
        mapping = {
            0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
            45: "fog", 48: "depositing rime fog", 51: "light drizzle", 53: "drizzle",
            55: "dense drizzle", 61: "slight rain", 63: "rain", 65: "heavy rain",
            71: "slight snow", 73: "snow", 75: "heavy snow", 80: "rain showers",
            81: "moderate rain showers", 82: "violent rain showers",
            95: "thunderstorm", 96: "thunderstorm with hail", 99: "severe thunderstorm",
        }
        return mapping.get(code, "unknown")


# ---------------------------------------------------------------------------
# Web search (DuckDuckGo HTML, retrieval-only)
# ---------------------------------------------------------------------------
class WebSearch:
    def __init__(self, net: NetworkManager):
        self.net = net

    def search(self, query: str, limit: int = 5) -> List[Dict]:
        cache_key = f"search:{query.lower()}"
        cached = self.net.cache_get(cache_key)
        if cached:
            try:
                return json.loads(cached)[:limit]
            except Exception:
                pass
        url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
        html = self.net.fetch_text(url)
        if not html:
            return []
        results = self._parse_ddg(html, limit)
        if results:
            self.net.cache_set(cache_key, json.dumps(results), ttl=3600)
        return results

    @staticmethod
    def _parse_ddg(html: str, limit: int) -> List[Dict]:
        import re
        results = []
        # Extract result links and snippets
        link_re = re.compile(r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.S)
        snippet_re = re.compile(r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>', re.S)
        links = link_re.findall(html)
        snippets = snippet_re.findall(html)
        for i, (href, title) in enumerate(links[:limit]):
            title_clean = re.sub(r"<[^>]+>", "", title).strip()
            snippet = re.sub(r"<[^>]+>", "", snippets[i]).strip() if i < len(snippets) else ""
            results.append({"title": title_clean, "url": href, "snippet": snippet})
        return results


# ---------------------------------------------------------------------------
# Facade
# ---------------------------------------------------------------------------
class WebManager:
    def __init__(self):
        self.net = NetworkManager()
        self.weather = WeatherService(self.net)
        self.search_engine = WebSearch(self.net)

    def search(self, query: str, limit: int = 5) -> List[Dict]:
        return self.search_engine.search(query, limit)

    def get_weather(self, location: Optional[str] = None) -> Dict:
        return self.weather.get_weather(location)

    def is_online(self) -> bool:
        return self.net.is_online()


_web: Optional[WebManager] = None


def get_web() -> WebManager:
    global _web
    if _web is None:
        _web = WebManager()
    return _web
