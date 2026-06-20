import requests
import sys

BACKEND_URL = "http://127.0.0.1:8000"

def test_india_telemetry():
    print("1. Creating Area of Interest in Visakhapatnam, India...")
    aoi_payload = {
        "name": "Visakhapatnam, IN",
        "latitude": 17.6868,
        "longitude": 83.2185,
        "radius_km": 15.0,
        "is_watched": True
    }
    
    # Register AOI
    res = requests.post(f"{BACKEND_URL}/aoi", json=aoi_payload)
    if res.status_code not in (200, 201):
        print(f"Error creating AOI: {res.status_code} - {res.text}")
        # Let's try listing AOIs and choosing a previous one if already exists
        list_res = requests.get(f"{BACKEND_URL}/aoi")
        aois = list_res.json()
        matching = [a for a in aois if a["name"] == "Visakhapatnam, IN"]
        if matching:
            area_id = matching[0]["id"]
            print(f"Found existing AOI ID: {area_id}")
        else:
            sys.exit(1)
    else:
        area_id = res.json()["id"]
        print(f"Created AOI with ID: {area_id}")

    print("\n2. Executing Search and triggering global telemetry ingestion...")
    search_payload = {
        "area_id": area_id,
        "modes": ["weather", "water", "vegetation"]
    }
    
    search_res = requests.post(f"{BACKEND_URL}/search", json=search_payload)
    if search_res.status_code != 200:
        print(f"Error calling search: {search_res.status_code} - {search_res.text}")
        sys.exit(1)
        
    data = search_res.json()
    readings = data.get("readings", [])
    report_text = data.get("report_text", "")
    provider_used = data.get("provider_used", "")
    
    print(f"\nReport generated successfully using provider: {provider_used}")
    print("--- Report Summary ---")
    # Print first few lines of report text
    print("\n".join(report_text.split("\n")[:10]) + "\n...")
    
    print(f"\nFetched total {len(readings)} readings.")
    
    # Group readings by metric type
    reading_types = {}
    for r in readings:
        m_type = r["metric_type"]
        source = r["source"]
        unit = r["unit"]
        if m_type not in reading_types:
            reading_types[m_type] = []
        reading_types[m_type].append(r["value"])
        
    print("\nIngested metrics count and average values:")
    for m_type, vals in reading_types.items():
        avg_val = sum(vals) / len(vals)
        print(f" - {m_type}: {len(vals)} readings, Average: {avg_val:.4f} {unit}")
        
    # Assertions
    assert "water_discharge" in reading_types, "Error: water_discharge metric not found for India!"
    assert "soil_moisture" in reading_types, "Error: soil_moisture metric not found for India!"
    print("\nSUCCESS: Global hydrology and soil moisture telemetry fetched successfully for India coordinates!")

if __name__ == "__main__":
    test_india_telemetry()
