import requests
import datetime
from typing import List, Any
from ingestion.base import normalize_reading, IngestionResult

OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

def fetch_open_meteo(aoi: Any) -> List[IngestionResult]:
    """
    Fetches the past 30 days of historical weather data (temperature and precipitation)
    from the Open-Meteo Archive API.
    """
    if isinstance(aoi, dict):
        aoi_id = aoi.get("id")
        lat = aoi.get("latitude")
        lon = aoi.get("longitude")
    else:
        aoi_id = getattr(aoi, "id", None) or aoi.id
        lat = getattr(aoi, "latitude", None) or aoi.latitude
        lon = getattr(aoi, "longitude", None) or aoi.longitude

    if lat is None or lon is None:
        raise ValueError("AOI must contain latitude and longitude")

    # Past 30 days range
    end_date = datetime.datetime.utcnow().date()
    start_date = end_date - datetime.timedelta(days=30)
    
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_str,
        "end_date": end_str,
        "daily": "temperature_2m_max,precipitation_sum",
        "timezone": "UTC"
    }

    try:
        response = requests.get(OPEN_METEO_ARCHIVE_URL, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        raise RuntimeError(f"Open-Meteo API request failed: {e}") from e

    daily = data.get("daily", {})
    dates = daily.get("time", [])
    temps = daily.get("temperature_2m_max", [])
    precips = daily.get("precipitation_sum", [])

    results = []

    for i in range(len(dates)):
        date_str = dates[i]
        
        # Parse temperature
        if i < len(temps) and temps[i] is not None:
            try:
                reading = normalize_reading(
                    area_id=aoi_id,
                    source="open_meteo",
                    metric_type="temperature",
                    value=temps[i],
                    unit="C",
                    reading_date=date_str
                )
                results.append(reading)
            except ValueError as e:
                print(f"Skipping invalid Open-Meteo temperature on {date_str}: {e}")

        # Parse precipitation
        if i < len(precips) and precips[i] is not None:
            try:
                reading = normalize_reading(
                    area_id=aoi_id,
                    source="open_meteo",
                    metric_type="precipitation",
                    value=precips[i],
                    unit="mm",
                    reading_date=date_str
                )
                results.append(reading)
            except ValueError as e:
                print(f"Skipping invalid Open-Meteo precipitation on {date_str}: {e}")

    return results
