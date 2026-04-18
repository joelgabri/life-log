import logging
from datetime import datetime, timezone

import httpx

from .. import schemas

logger = logging.getLogger(__name__)

_OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
_CURRENT_FIELDS = "temperature_2m,precipitation,wind_speed_10m,weather_code"


def weather_external_id(lat: float, lon: float, tst: int) -> str:
    bucket = (tst // 1800) * 1800
    return f"weather:{round(lat, 2):.2f}:{round(lon, 2):.2f}:{bucket}"


def fetch_weather_entry(lat: float, lon: float, tst: int) -> schemas.EntryCreate | None:
    """Fetch current weather from Open-Meteo. Returns EntryCreate or None on failure."""
    bucket_ts = (tst // 1800) * 1800
    external_id = f"weather:{round(lat, 2):.2f}:{round(lon, 2):.2f}:{bucket_ts}"

    try:
        resp = httpx.get(
            _OPEN_METEO_URL,
            params={"latitude": lat, "longitude": lon, "current": _CURRENT_FIELDS},
            timeout=5.0,
        )
        resp.raise_for_status()
        current = resp.json()["current"]
    except Exception:
        logger.warning("Weather fetch failed for lat=%s lon=%s", lat, lon, exc_info=True)
        return None

    return schemas.EntryCreate(
        type="weather",
        source="open-meteo",
        external_id=external_id,
        timestamp=datetime.fromtimestamp(bucket_ts, tz=timezone.utc),
        data={
            "lat": lat,
            "lon": lon,
            "temperature_2m": current.get("temperature_2m"),
            "precipitation": current.get("precipitation"),
            "wind_speed_10m": current.get("wind_speed_10m"),
            "weather_code": current.get("weather_code"),
        },
    )
