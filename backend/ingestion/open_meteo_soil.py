import requests
import datetime
from typing import List, Dict, Any
from ingestion.base import normalize_reading, IngestionResult

OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

def fetch_open_meteo_soil(aoi: Any) -> List[IngestionResult]:
    """
    Fetches the past 30 days of hourly soil moisture data from Open-Meteo Forecast API
    and aggregates them into daily averages.
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

    params = {
        "latitude": lat,
        "longitude": lon,
        "past_days": 30,
        "hourly": "soil_moisture_0_to_7cm"
    }

    try:
        response = requests.get(OPEN_METEO_FORECAST_URL, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"Open-Meteo Forecast/Soil API request failed: {e}")
        return []

    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    moistures = hourly.get("soil_moisture_0_to_7cm", [])

    # Group hourly values by date (YYYY-MM-DD)
    daily_values: Dict[str, List[float]] = {}
    for i in range(len(times)):
        time_str = times[i]
        val = moistures[i]
        
        if val is None or not time_str:
            continue
            
        # Extract date portion YYYY-MM-DD
        date_str = time_str[:10]
        if date_str not in daily_values:
            daily_values[date_str] = []
        daily_values[date_str].append(val)

    # Compute daily averages and create IngestionResult list
    results = []
    # Open-Meteo returns future forecast days too if we don't filter.
    # We only want past/current days (up to today)
    today_str = datetime.datetime.utcnow().date().isoformat()

    for date_str, vals in daily_values.items():
        # Only ingest up to today's date (no forecast predictions)
        if date_str > today_str:
            continue
            
        if not vals:
            continue
            
        avg_val = sum(vals) / len(vals)
        try:
            reading = normalize_reading(
                area_id=aoi_id,
                source="open_meteo",
                metric_type="soil_moisture",
                value=avg_val,
                unit="m3/m3",
                reading_date=date_str
            )
            results.append(reading)
        except ValueError as e:
            print(f"Skipping invalid soil moisture reading on {date_str}: {e}")

    return results
