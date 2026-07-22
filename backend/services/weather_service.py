"""
External weather API integration (OpenWeatherMap).
Alert creation remains manual — this only fetches display data.
"""

import httpx
from config import get_settings

settings = get_settings()


async def fetch_current_weather(lat: float, lon: float) -> dict | None:
    """Fetch current weather for a coordinate from OpenWeatherMap."""
    if not settings.WEATHER_API_KEY:
        return None

    url = f"{settings.WEATHER_API_BASE_URL}/weather"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": settings.WEATHER_API_KEY,
        "units": "metric",
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        return {
            "temp": data["main"]["temp"],
            "feels_like": data["main"]["feels_like"],
            "humidity": data["main"]["humidity"],
            "wind_speed": data["wind"]["speed"],
            "description": data["weather"][0]["description"] if data.get("weather") else None,
            "icon": data["weather"][0]["icon"] if data.get("weather") else None,
        }
    except Exception:
        return None


async def fetch_forecast(lat: float, lon: float, days: int = 6) -> list[dict]:
    """Fetch multi-day forecast from OpenWeatherMap."""
    if not settings.WEATHER_API_KEY:
        return []

    url = f"{settings.WEATHER_API_BASE_URL}/forecast"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": settings.WEATHER_API_KEY,
        "units": "metric",
        "cnt": days * 8,  # 3-hour intervals
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        # Group by day, take noon reading
        daily = {}
        for item in data.get("list", []):
            date = item["dt_txt"].split(" ")[0]
            hour = int(item["dt_txt"].split(" ")[1].split(":")[0])
            if date not in daily or abs(hour - 12) < abs(daily[date]["_hour"] - 12):
                daily[date] = {
                    "_hour": hour,
                    "date": date,
                    "temp_max": item["main"]["temp_max"],
                    "temp_min": item["main"]["temp_min"],
                    "humidity": item["main"]["humidity"],
                    "rain_chance": item.get("pop", 0) * 100,
                    "description": item["weather"][0]["description"] if item.get("weather") else None,
                }

        result = list(daily.values())[:days]
        for r in result:
            r.pop("_hour", None)
        return result
    except Exception:
        return []
