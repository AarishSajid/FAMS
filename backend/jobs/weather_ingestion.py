"""
Background job to pre-fetch weather data hourly.
In a real app, this would cache data in Redis per district/coordinate.
For now, this is a stub that logs execution, as the actual dashboard
will call `fetch_current_weather` dynamically or hit the cache.
"""

import logging
from services.weather_service import fetch_current_weather

logger = logging.getLogger("fams.jobs.weather")


async def run_weather_ingestion():
    """APScheduler wrapper for hourly weather ingestion."""
    logger.info("Running scheduled weather ingestion job...")
    # Example coordinates for Sheikhupura/Layyah
    # In reality, iterate over District table coordinates and cache in Redis.
    coords = [(31.7167, 73.9850), (30.9693, 70.9428)]
    
    for lat, lon in coords:
        try:
            data = await fetch_current_weather(lat, lon)
            if data:
                logger.info(f"Fetched weather for ({lat}, {lon}): {data['temp']}°C, {data['description']}")
                # redis_client.set(f"weather:{lat}:{lon}", json.dumps(data), ex=3600)
        except Exception as e:
            logger.error(f"Error fetching weather for ({lat}, {lon}): {e}")
