import requests
import datetime
import math
from typing import List, Dict, Any, Tuple
from ingestion.base import normalize_reading, IngestionResult

USGS_IV_URL = "https://waterservices.usgs.gov/nwis/iv/"

def calculate_bbox(lat: float, lon: float, radius_km: float) -> str:
    """Calculates bounding box coordinates string (west,south,east,north) for USGS."""
    # 1 degree latitude = 111 km
    lat_delta = radius_km / 111.0
    
    # 1 degree longitude = 111 * cos(lat) km
    cos_lat = math.cos(math.radians(lat))
    if cos_lat == 0:
        lon_delta = radius_km / 111.0
    else:
        lon_delta = radius_km / (111.0 * abs(cos_lat))
        
    west = lon - lon_delta
    east = lon + lon_delta
    south = lat - lat_delta
    north = lat + lat_delta
    
    return f"{west:.6f},{south:.6f},{east:.6f},{north:.6f}"

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Simple Euclidean distance calculation."""
    return math.sqrt((lat1 - lat2)**2 + (lon1 - lon2)**2)

def fetch_usgs_water(aoi: Any) -> List[IngestionResult]:
    """
    Fetches the past 30 days of water data (discharge and gauge height)
    from the USGS NWIS Instantaneous Value service for the nearest station.
    """
    if isinstance(aoi, dict):
        aoi_id = aoi.get("id")
        lat = aoi.get("latitude")
        lon = aoi.get("longitude")
        radius_km = aoi.get("radius_km", 10.0)
    else:
        aoi_id = getattr(aoi, "id", None) or aoi.id
        lat = getattr(aoi, "latitude", None) or aoi.latitude
        lon = getattr(aoi, "longitude", None) or aoi.longitude
        radius_km = getattr(aoi, "radius_km", 10.0)

    if lat is None or lon is None:
        raise ValueError("AOI must contain latitude and longitude")

    # Generate USGS Bounding Box
    bbox_str = calculate_bbox(lat, lon, radius_km)

    # Past 30 days range
    end_date = datetime.datetime.utcnow().date()
    start_date = end_date - datetime.timedelta(days=30)
    
    params = {
        "format": "json",
        "bBox": bbox_str,
        "parameterCd": "00060,00065", # 00060: discharge, 00065: gauge height
        "startDT": start_date.isoformat(),
        "endDT": end_date.isoformat(),
        "siteStatus": "active"
    }

    try:
        response = requests.get(USGS_IV_URL, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        # USGS may fail if coordinates are outside the US, since it has no coverage
        print(f"USGS Water API request failed or returned empty: {e}")
        return []

    time_series_list = data.get("value", {}).get("timeSeries", [])
    if not time_series_list:
        print("No active USGS water stations found in this AOI bounding box.")
        return []

    # 1. Group timeSeries by site to find the nearest site
    sites_info = {}
    for ts in time_series_list:
        source_info = ts.get("sourceInfo", {})
        site_code_list = source_info.get("siteCode", [])
        if not site_code_list:
            continue
        site_code = site_code_list[0].get("value")
        
        if site_code not in sites_info:
            geo_loc = source_info.get("geoLocation", {}).get("geogLocation", {})
            site_lat = geo_loc.get("latitude")
            site_lon = geo_loc.get("longitude")
            
            if site_lat is not None and site_lon is not None:
                dist = calculate_distance(lat, lon, site_lat, site_lon)
                sites_info[site_code] = {
                    "code": site_code,
                    "name": source_info.get("siteName", "Unnamed Station"),
                    "distance": dist,
                    "ts_items": []
                }
        
        if site_code in sites_info:
            sites_info[site_code]["ts_items"].append(ts)

    if not sites_info:
        return []

    # Find closest site
    nearest_site_code = min(sites_info.keys(), key=lambda k: sites_info[k]["distance"])
    nearest_site = sites_info[nearest_site_code]
    print(f"Closest USGS station selected: {nearest_site['name']} ({nearest_site_code}), distance delta: {nearest_site['distance']:.4f}")

    results = []

    # 2. Extract values from nearest site's time series
    for ts in nearest_site["ts_items"]:
        var_code_list = ts.get("variable", {}).get("variableCode", [])
        if not var_code_list:
            continue
        var_code = var_code_list[0].get("value")
        
        # Map parameter code to metric type
        if var_code == "00060":
            metric_type = "water_discharge"
            unit = "cfs"
        elif var_code == "00065":
            metric_type = "gauge_height"
            unit = "ft"
        else:
            continue

        values_list = ts.get("values", [])
        if not values_list:
            continue
        
        # Group instantaneous readings by date to compute daily averages
        daily_readings: Dict[str, List[float]] = {}
        for item in values_list[0].get("value", []):
            val_str = item.get("value")
            dt_str = item.get("dateTime")
            
            if not val_str or not dt_str:
                continue
                
            try:
                # Convert string to float
                val = float(val_str)
                # Parse date portion: YYYY-MM-DD
                d_str = dt_str[:10]
                
                if d_str not in daily_readings:
                    daily_readings[d_str] = []
                daily_readings[d_str].append(val)
            except ValueError:
                continue

        # Create daily IngestionResult entries
        for d_str, vals in daily_readings.items():
            if not vals:
                continue
            avg_val = sum(vals) / len(vals)
            try:
                reading = normalize_reading(
                    area_id=aoi_id,
                    source="usgs_water",
                    metric_type=metric_type,
                    value=avg_val,
                    unit=unit,
                    reading_date=d_str
                )
                results.append(reading)
            except ValueError as e:
                print(f"Skipping invalid USGS reading for {metric_type} on {d_str}: {e}")

    return results
