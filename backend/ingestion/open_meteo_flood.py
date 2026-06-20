import requests
import datetime
from typing import List, Any
from ingestion.base import normalize_reading, IngestionResult

OPEN_METEO_FLOOD_URL = "https://flood-api.open-meteo.com/v1/flood"

def fetch_open_meteo_flood(aoi: Any) -> List[IngestionResult]:
    """
    Fetches the past 30 days of global river discharge data from the Open-Meteo Flood API.
    Values are converted from m3/s to cfs (cubic feet per second) to align with USGS schema.
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

    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "river_discharge",
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d")
    }

    try:
        response = requests.get(OPEN_METEO_FLOOD_URL, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"Open-Meteo Flood API request failed: {e}")
        return []

    daily = data.get("daily", {})
    dates = daily.get("time", [])
    discharges = daily.get("river_discharge", [])

    results = []
    # 1 m3/s = 35.3147 cfs
    M3_TO_CFS = 35.3147

    for i in range(len(dates)):
        date_str = dates[i]
        val = discharges[i]
        
        if val is None:
            continue
            
        try:
            # Convert m3/s to cfs for consistency with water_discharge unit
            val_cfs = val * M3_TO_CFS
            reading = normalize_reading(
                area_id=aoi_id,
                source="open_meteo",
                metric_type="water_discharge",
                value=val_cfs,
                unit="cfs",
                reading_date=date_str
            )
            results.append(reading)
        except ValueError as e:
            print(f"Skipping invalid flood reading on {date_str}: {e}")

    return results
