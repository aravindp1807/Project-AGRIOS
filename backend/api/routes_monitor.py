from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
from db.connection import get_db

router = APIRouter(prefix="/monitor", tags=["Monitor Mode"])

class AlertResponse(BaseModel):
    id: int
    metric_type: str
    severity: str
    message: str
    triggered_at: str
    acknowledged: bool

class ReadingResponse(BaseModel):
    source: str
    metric_type: str
    value: float
    unit: str
    reading_date: str

class MonitorDataResponse(BaseModel):
    readings: List[ReadingResponse]
    alerts: List[AlertResponse]

class CachedReportResponse(BaseModel):
    report_text: str
    modes_included: List[str]
    llm_provider_used: str
    generated_at: str

@router.get("/{area_id}", response_model=MonitorDataResponse)
def get_monitor_data(area_id: str):
    # Verify area exists
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM areas_of_interest WHERE id = ?", (area_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Area of Interest not found")
            
        # Get readings
        cursor.execute(
            """
            SELECT source, metric_type, value, unit, reading_date 
            FROM readings WHERE area_id = ?
            ORDER BY reading_date DESC LIMIT 500
            """,
            (area_id,)
        )
        readings = []
        for row in cursor.fetchall():
            readings.append({
                "source": row["source"],
                "metric_type": row["metric_type"],
                "value": row["value"],
                "unit": row["unit"],
                "reading_date": row["reading_date"]
            })
            
        # Get active alerts
        cursor.execute(
            """
            SELECT id, metric_type, severity, message, triggered_at, acknowledged 
            FROM alerts WHERE area_id = ? AND acknowledged = 0
            ORDER BY triggered_at DESC
            """,
            (area_id,)
        )
        alerts = []
        for row in cursor.fetchall():
            alerts.append({
                "id": row["id"],
                "metric_type": row["metric_type"],
                "severity": row["severity"],
                "message": row["message"],
                "triggered_at": row["triggered_at"],
                "acknowledged": bool(row["acknowledged"])
            })
            
    return {
        "readings": readings,
        "alerts": alerts
    }

@router.get("/{area_id}/report", response_model=CachedReportResponse)
def get_latest_report(area_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM areas_of_interest WHERE id = ?", (area_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Area of Interest not found")
            
        cursor.execute(
            """
            SELECT report_text, modes_included, llm_provider_used, generated_at 
            FROM reports WHERE area_id = ?
            ORDER BY generated_at DESC LIMIT 1
            """,
            (area_id,)
        )
        row = cursor.fetchone()
        
    if not row:
        raise HTTPException(
            status_code=404, 
            detail="No reports found for this Area of Interest yet. Run a Search first, or verify if the monitoring cycle has executed."
        )
        
    try:
        modes = json.loads(row["modes_included"])
    except Exception:
        modes = []
        
    return {
        "report_text": row["report_text"],
        "modes_included": modes,
        "llm_provider_used": row["llm_provider_used"],
        "generated_at": row["generated_at"]
    }

@router.post("/alert/{alert_id}/acknowledge", status_code=status.HTTP_200_OK)
def acknowledge_alert(alert_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM alerts WHERE id = ?", (alert_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Alert not found")
            
        cursor.execute(
            "UPDATE alerts SET acknowledged = 1 WHERE id = ?",
            (alert_id,)
        )
        conn.commit()
        
    return {"message": f"Alert {alert_id} marked as acknowledged."}
