import time
import os
import json
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from db.connection import get_db
from ingestion.nasa_power import fetch_nasa_power
from ingestion.open_meteo import fetch_open_meteo
from ingestion.usgs_water import fetch_usgs_water
from processing.baselines import recompute_and_save_baseline
from processing.trends import detect_trend_for_area_metric
from analysis.alerting import check_and_create_alerts
from analysis.llm_router import LLMRouter
from analysis.prompts import SYNTHESIS_USER_TEMPLATE

def run_monitor_cycle():
    """
    Executes a full monitoring polling cycle for all watched Areas of Interest (AOIs).
    Runs API fetches, database persistence, trend recalculation, and AI report synthesis.
    """
    print(f"[{datetime.now()}] Starting scheduled monitor cycle...")
    
    # 1. Fetch watched areas
    watched_areas = []
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, latitude, longitude, radius_km FROM areas_of_interest WHERE is_watched = 1")
        for row in cursor.fetchall():
            watched_areas.append({
                "id": row["id"],
                "name": row["name"],
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "radius_km": row["radius_km"]
            })
            
    print(f"Found {len(watched_areas)} watched areas.")
    
    for area in watched_areas:
        print(f"Monitoring Area: {area['name']} ({area['id']})")
        
        # 2. Ingest from all sources
        fetched_readings = []
        
        # Ingest NASA Power
        try:
            start_time = time.time()
            readings = fetch_nasa_power(area)
            fetched_readings.extend(readings)
            duration_ms = int((time.time() - start_time) * 1000)
            with get_db() as conn:
                conn.cursor().execute("INSERT INTO collection_logs (area_id, source, status, response_time_ms) VALUES (?, 'nasa_power', 'success', ?)", (area["id"], duration_ms))
                conn.commit()
        except Exception as e:
            print(f"Error fetching nasa_power for {area['name']}: {e}")
            
        # Ingest Open-Meteo Weather
        try:
            start_time = time.time()
            readings = fetch_open_meteo(area)
            fetched_readings.extend(readings)
            duration_ms = int((time.time() - start_time) * 1000)
            with get_db() as conn:
                conn.cursor().execute("INSERT INTO collection_logs (area_id, source, status, response_time_ms) VALUES (?, 'open_meteo', 'success', ?)", (area["id"], duration_ms))
                conn.commit()
        except Exception as e:
            print(f"Error fetching open_meteo for {area['name']}: {e}")
            
        # Ingest USGS Water with global Flood API fallback
        water_readings = []
        try:
            start_time = time.time()
            water_readings = fetch_usgs_water(area)
            fetched_readings.extend(water_readings)
            duration_ms = int((time.time() - start_time) * 1000)
            if water_readings:
                with get_db() as conn:
                    conn.cursor().execute("INSERT INTO collection_logs (area_id, source, status, response_time_ms) VALUES (?, 'usgs_water', 'success', ?)", (area["id"], duration_ms))
                    conn.commit()
        except Exception as e:
            print(f"Error fetching usgs_water for {area['name']}: {e}")
            
        if not water_readings:
            try:
                start_time = time.time()
                from ingestion.open_meteo_flood import fetch_open_meteo_flood
                flood_readings = fetch_open_meteo_flood(area)
                fetched_readings.extend(flood_readings)
                duration_ms = int((time.time() - start_time) * 1000)
                if flood_readings:
                    with get_db() as conn:
                        conn.cursor().execute("INSERT INTO collection_logs (area_id, source, status, response_time_ms) VALUES (?, 'open_meteo_flood', 'success', ?)", (area["id"], duration_ms))
                        conn.commit()
            except Exception as e:
                print(f"Error fetching open_meteo_flood for {area['name']}: {e}")
                
        # Ingest Open-Meteo Soil Moisture
        try:
            start_time = time.time()
            from ingestion.open_meteo_soil import fetch_open_meteo_soil
            soil_readings = fetch_open_meteo_soil(area)
            fetched_readings.extend(soil_readings)
            duration_ms = int((time.time() - start_time) * 1000)
            if soil_readings:
                with get_db() as conn:
                    conn.cursor().execute("INSERT INTO collection_logs (area_id, source, status, response_time_ms) VALUES (?, 'open_meteo_soil', 'success', ?)", (area["id"], duration_ms))
                    conn.commit()
        except Exception as e:
            print(f"Error fetching open_meteo_soil for {area['name']}: {e}")

        # 3. Save all readings to DB
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
            
        # Check if we have any existing metrics in DB if no new ones fetched
        if not metric_types_to_update:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT metric_type FROM readings WHERE area_id = ?", (area["id"],))
                metric_types_to_update = {row["metric_type"] for row in cursor.fetchall()}

        # 4. Recompute baselines, detect trends, check alerts
        trends_map = {}
        metrics_list_for_fallback = []
        formatted_metrics_strings = []
        
        with get_db() as conn:
            for metric in metric_types_to_update:
                # Recalculate 30-day and 90-day baselines
                recompute_and_save_baseline(conn, area["id"], metric, 30)
                recompute_and_save_baseline(conn, area["id"], metric, 90)
                
                # Recalculate trends
                trend_res = detect_trend_for_area_metric(conn, area["id"], metric)
                if trend_res:
                    trends_map[metric] = trend_res
                    
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT value, unit FROM readings WHERE area_id = ? AND metric_type = ? ORDER BY reading_date DESC LIMIT 1",
                        (area["id"], metric)
                    )
                    latest_row = cursor.fetchone()
                    
                    cursor.execute(
                        "SELECT avg_value FROM baselines WHERE area_id = ? AND metric_type = ? AND window_days = 30",
                        (area["id"], metric)
                    )
                    baseline_row = cursor.fetchone()
                    
                    if latest_row and baseline_row:
                        latest_val = latest_row["value"]
                        unit = latest_row["unit"]
                        base_val = baseline_row["avg_value"]
                        
                        metric_str = (
                            f"- {metric}: current value: {latest_val} {unit}, "
                            f"30-day baseline: {base_val:.2f} {unit}, "
                            f"deviation: {trend_res.deviation_pct:+.1f}%, "
                            f"trend: {trend_res.direction}"
                        )
                        formatted_metrics_strings.append(metric_str)
                        metrics_list_for_fallback.append({
                            "name": metric,
                            "value": latest_val,
                            "unit": unit,
                            "baseline": base_val,
                            "deviation_pct": trend_res.deviation_pct,
                            "direction": trend_res.direction
                        })

            # Check thresholds and trigger alerts
            triggered = check_and_create_alerts(conn, area["id"], trends_map)
            if triggered:
                print(f"Triggered {len(triggered)} alerts for {area['name']}: {triggered}")

        # 5. Synthesize background LLM report (cached)
        if formatted_metrics_strings:
            prompt = SYNTHESIS_USER_TEMPLATE.format(
                aoi_name=area["name"],
                lat=area["latitude"],
                lon=area["longitude"],
                modes_list="weather, water",
                formatted_metrics="\n".join(formatted_metrics_strings)
            )
            
            fallback_context = {
                "aoi_name": area["name"],
                "metrics": metrics_list_for_fallback
            }
            
            router = LLMRouter()
            # Background task: task_type="monitor" (prevents using tight-rate-limit Groq API)
            synthesis = router.synthesize(prompt, task_type="monitor", fallback_context_data=fallback_context)
            
            # Save report
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO reports (area_id, report_text, modes_included, llm_provider_used)
                    VALUES (?, ?, ?, ?)
                    """,
                    (area["id"], synthesis.text, json.dumps(["weather", "water"]), synthesis.provider_used)
                )
                conn.commit()
            print(f"Cached background report for {area['name']} using {synthesis.provider_used}")

    print(f"[{datetime.now()}] Monitored cycle finished.")

def start_monitor_scheduler():
    """Initializes and starts the APScheduler background thread."""
    scheduler = BackgroundScheduler()
    # Trigger first run immediately on startup, then execute every 6 hours
    scheduler.add_job(
        run_monitor_cycle, 
        'interval', 
        hours=6, 
        id="agrios_monitor_job", 
        replace_existing=True, 
        next_run_time=datetime.now()
    )
    scheduler.start()
