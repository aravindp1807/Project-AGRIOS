import requests
import datetime
from typing import List, Any
from ingestion.base import normalize_reading, IngestionResult

NASA_POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"

def fetch_nasa_power(aoi: Any) -> List[IngestionResult]:
    """
    Fetches the past 30 days of weather/climate data from NASA POWER API.
    
    aoi must have properties:
      - id (str)
      - latitude (float)
      - longitude (float)
    """
    # Extract properties (support both object and dict)
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
    
    start_str = start_date.strftime("%Y%m%d")
    end_str = end_date.strftime("%Y%m%d")

    params = {
        "parameters": "T2M,PRECTOTCORR,ALLSKY_SFC_SW_DWN",
        "community": "AG",
        "longitude": lon,
        "latitude": lat,
        "start": start_str,
        "end": end_str,
        "format": "JSON"
    }

    try:
        response = requests.get(NASA_POWER_URL, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        # Wrap exception to log/handle upsteam
        raise RuntimeError(f"NASA POWER API request failed: {e}") from e

    properties = data.get("properties", {})
    parameter = properties.get("parameter", {})

    results = []

    # Map of NASA POWER parameter name -> AGRIOS metric_type & unit
    metric_mapping = {
        "T2M": ("temperature", "C"),
        "PRECTOTCORR": ("precipitation", "mm"),
        "ALLSKY_SFC_SW_DWN": ("solar_radiation", "MJ/m2/day")
    }

    for param_name, (metric_type, unit) in metric_mapping.items():
        param_data = parameter.get(param_name, {})
        for date_str, val in param_data.items():
            # Skip missing/fill value (-999 or similar indicator)
            if val is None or val < -900:
                continue
            try:
                reading = normalize_reading(
                    area_id=aoi_id,
                    source="nasa_power",
                    metric_type=metric_type,
                    value=val,
                    unit=unit,
                    reading_date=date_str
                )
                results.append(reading)
            except ValueError as e:
                # Log single reading error but continue parsing other values
                print(f"Skipping invalid reading for {metric_type} on {date_str}: {e}")

    return results
