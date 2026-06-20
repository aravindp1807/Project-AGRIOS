from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
from datetime import datetime
from db.connection import get_db
from ingestion.nasa_power import fetch_nasa_power
from ingestion.open_meteo import fetch_open_meteo
from ingestion.usgs_water import fetch_usgs_water
from processing.baselines import recompute_and_save_baseline
from processing.trends import detect_trend_for_area_metric
from analysis.llm_router import LLMRouter
from analysis.prompts import SYNTHESIS_USER_TEMPLATE

router = APIRouter(prefix="/search", tags=["Search Mode"])

class SearchRequest(BaseModel):
    area_id: str
    modes: List[str] # ["weather", "water", "vegetation"]

class ReadingResponse(BaseModel):
    source: str
    metric_type: str
    value: float
    unit: str
    reading_date: str

class SearchResponse(BaseModel):
    area_id: str
    report_text: str
    provider_used: str
    readings: List[ReadingResponse]

@router.post("", response_model=SearchResponse)
def execute_search(req: SearchRequest):
    # 1. Fetch AOI
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, latitude, longitude, radius_km FROM areas_of_interest WHERE id = ?", (req.area_id,))
        aoi = cursor.fetchone()
        
    if not aoi:
        raise HTTPException(status_code=404, detail="Area of Interest not found")
        
    aoi_data = {
        "id": aoi["id"],
        "name": aoi["name"],
        "latitude": aoi["latitude"],
        "longitude": aoi["longitude"],
        "radius_km": aoi["radius_km"]
    }

    # 2. Trigger fetches based on modes
    fetched_readings = []
    
    if "weather" in req.modes:
        try:
            fetched_readings.extend(fetch_nasa_power(aoi_data))
        except Exception as e:
            print(f"NASA POWER fetch failed during search: {e}")
            
        try:
            fetched_readings.extend(fetch_open_meteo(aoi_data))
        except Exception as e:
            print(f"Open-Meteo fetch failed during search: {e}")
            
    if "water" in req.modes:
        usgs_readings = []
        try:
            usgs_readings = fetch_usgs_water(aoi_data)
            fetched_readings.extend(usgs_readings)
        except Exception as e:
            print(f"USGS water fetch failed during search: {e}")
            
        if not usgs_readings:
            try:
                from ingestion.open_meteo_flood import fetch_open_meteo_flood
                flood_readings = fetch_open_meteo_flood(aoi_data)
                if flood_readings:
                    print(f"USGS empty. Loaded {len(flood_readings)} global river discharge readings from Open-Meteo Flood API.")
                    fetched_readings.extend(flood_readings)
            except Exception as e:
                print(f"Open-Meteo Flood API fallback fetch failed: {e}")

    if "vegetation" in req.modes:
        try:
            from ingestion.open_meteo_soil import fetch_open_meteo_soil
            soil_readings = fetch_open_meteo_soil(aoi_data)
            if soil_readings:
                print(f"Loaded {len(soil_readings)} soil moisture readings from Open-Meteo.")
                fetched_readings.extend(soil_readings)
        except Exception as e:
            print(f"Open-Meteo Soil moisture fetch failed: {e}")

    # 3. Save readings to DB & collect metric types
    metric_types_to_update = set()
    
    with get_db() as conn:
        cursor = conn.cursor()
        for r in fetched_readings:
            metric_types_to_update.add(r.metric_type)
            cursor.execute(
                """
                INSERT INTO readings (area_id, source, metric_type, value, unit, reading_date)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(area_id, source, metric_type, reading_date)
                DO UPDATE SET value = excluded.value, fetched_at = CURRENT_TIMESTAMP
                """,
                (r.area_id, r.source, r.metric_type, r.value, r.unit, r.reading_date.isoformat())
            )
        conn.commit()

    # If no new readings were fetched, inspect what existing metrics are in the DB
    if not metric_types_to_update:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT metric_type FROM readings WHERE area_id = ?", (req.area_id,))
            metric_types_to_update = {row["metric_type"] for row in cursor.fetchall()}

    # 4. Recompute Baselines and Trends
    trends_map = {}
    metrics_list_for_fallback = []
    formatted_metrics_strings = []

    with get_db() as conn:
        for metric in metric_types_to_update:
            # Recompute 30-day and 90-day baselines
            recompute_and_save_baseline(conn, req.area_id, metric, 30)
            recompute_and_save_baseline(conn, req.area_id, metric, 90)
            
            # Detect trend
            trend_res = detect_trend_for_area_metric(conn, req.area_id, metric)
            if trend_res:
                trends_map[metric] = trend_res
                
                # Fetch latest reading and 30-day baseline to build context
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT value, unit FROM readings WHERE area_id = ? AND metric_type = ? ORDER BY reading_date DESC LIMIT 1",
                    (req.area_id, metric)
                )
                latest_row = cursor.fetchone()
                
                cursor.execute(
                    "SELECT avg_value FROM baselines WHERE area_id = ? AND metric_type = ? AND window_days = 30",
                    (req.area_id, metric)
                )
                baseline_row = cursor.fetchone()
                
                if latest_row and baseline_row:
                    latest_val = latest_row["value"]
                    unit = latest_row["unit"]
                    base_val = baseline_row["avg_value"]
                    
                    # Format for LLM prompt context
                    metric_str = (
                        f"- {metric}: current value: {latest_val} {unit}, "
                        f"30-day baseline: {base_val:.2f} {unit}, "
                        f"deviation: {trend_res.deviation_pct:+.1f}%, "
                        f"trend: {trend_res.direction}"
                    )
                    formatted_metrics_strings.append(metric_str)
                    
                    # Store in dict for local rule-based fallback
                    metrics_list_for_fallback.append({
                        "name": metric,
                        "value": latest_val,
                        "unit": unit,
                        "baseline": base_val,
                        "deviation_pct": trend_res.deviation_pct,
                        "direction": trend_res.direction
                    })

    # 5. Synthesize LLM Report
    report_text = ""
    provider_used = "none"
    
    if formatted_metrics_strings:
        prompt = SYNTHESIS_USER_TEMPLATE.format(
            aoi_name=aoi_data["name"],
            lat=aoi_data["latitude"],
            lon=aoi_data["longitude"],
            modes_list=", ".join(req.modes),
            formatted_metrics="\n".join(formatted_metrics_strings)
        )
        
        fallback_context = {
            "aoi_name": aoi_data["name"],
            "metrics": metrics_list_for_fallback
        }
        
        router = LLMRouter()
        synthesis = router.synthesize(prompt, task_type="search", fallback_context_data=fallback_context)
        report_text = synthesis.text
        provider_used = synthesis.provider_used
        
        # Cache report in DB
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO reports (area_id, report_text, modes_included, llm_provider_used)
                VALUES (?, ?, ?, ?)
                """,
                (req.area_id, report_text, json.dumps(req.modes), provider_used)
            )
            conn.commit()
    else:
        report_text = f"No environmental readings found for {aoi_data['name']}. Please try another mode or wait for data ingestion."
        provider_used = "system"

    # 6. Fetch all readings to return in response
    readings_to_return = []
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT source, metric_type, value, unit, reading_date FROM readings 
            WHERE area_id = ?
            ORDER BY reading_date DESC LIMIT 100
            """,
            (req.area_id,)
        )
        for row in cursor.fetchall():
            readings_to_return.append({
                "source": row["source"],
                "metric_type": row["metric_type"],
                "value": row["value"],
                "unit": row["unit"],
                "reading_date": row["reading_date"]
            })

    return {
        "area_id": req.area_id,
        "report_text": report_text,
        "provider_used": provider_used,
        "readings": readings_to_return
    }
