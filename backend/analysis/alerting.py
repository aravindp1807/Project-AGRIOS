from typing import Dict, List, Optional
from datetime import datetime, timedelta
from processing.trends import TrendResult

# Default configurable thresholds
WARNING_MIN_DEV = 15.0
CRITICAL_MIN_DEV = 30.0

def evaluate_metric_alerts(
    area_id: str,
    metric_type: str,
    trend: TrendResult,
    baseline: float,
    recent_readings: List[float]
) -> Optional[Dict[str, str]]:
    """
    Checks alert conditions for a single metric.
    Returns a dict with {'severity': ..., 'message': ...} if alert triggers, else None.
    """
    if baseline is None or baseline == 0:
        return None
        
    dev_abs = abs(trend.deviation_pct)
    
    # 1. Check critical deviation threshold (>30%)
    if dev_abs >= CRITICAL_MIN_DEV:
        return {
            "severity": "critical",
            "message": f"Critical deviation! {metric_type.replace('_', ' ').capitalize()} is {trend.deviation_pct:.1f}% deviated from 30-day baseline of {baseline:.2f} (current: {recent_readings[-1] if recent_readings else 'N/A'})."
        }
        
    # 2. Check 3+ consecutive readings trending the same direction beyond warning threshold (15%)
    if len(recent_readings) >= 3:
        last_three = recent_readings[-3:]
        # Check if all last 3 values are beyond the 15% threshold
        all_beyond_warning = all(
            abs((v - baseline) / baseline) * 100 >= WARNING_MIN_DEV 
            for v in last_three
        )
        if all_beyond_warning:
            # Check if they are strictly rising or strictly falling
            is_rising = last_three[0] < last_three[1] < last_three[2]
            is_falling = last_three[0] > last_three[1] > last_three[2]
            if is_rising or is_falling:
                trend_word = "rising" if is_rising else "falling"
                return {
                    "severity": "critical",
                    "message": f"Critical trend warning! {metric_type.replace('_', ' ').capitalize()} has had 3 consecutive readings {trend_word} beyond the warning threshold (current: {last_three[-1]}, baseline: {baseline:.2f})."
                }

    # 3. Check warning deviation threshold (15%-30%)
    if dev_abs >= WARNING_MIN_DEV:
        return {
            "severity": "warning",
            "message": f"{metric_type.replace('_', ' ').capitalize()} shows {trend.deviation_pct:.1f}% deviation from 30-day baseline of {baseline:.2f}."
        }
        
    return None

def check_and_create_alerts(conn, area_id: str, trends: Dict[str, TrendResult]) -> List[Dict[str, Any]]:
    """
    Checks all metric trends for an area, evaluates alert thresholds, 
    and inserts new alerts into the SQLite database.
    """
    cursor = conn.cursor()
    triggered_alerts = []
    
    # Get 30-day baseline for each metric
    cursor.execute(
        "SELECT metric_type, avg_value FROM baselines WHERE area_id = ? AND window_days = 30",
        (area_id,)
    )
    baselines = {row["metric_type"]: row["avg_value"] for row in cursor.fetchall()}
    
    # Get last 5 readings for each metric (ordered chronologically)
    cutoff_date = (datetime.utcnow() - timedelta(days=30)).date()
    cursor.execute(
        """
        SELECT metric_type, value FROM readings 
        WHERE area_id = ? AND reading_date >= ?
        ORDER BY reading_date ASC
        """,
        (area_id, cutoff_date.isoformat())
    )
    readings_by_metric = {}
    for r in cursor.fetchall():
        m_type = r["metric_type"]
        if m_type not in readings_by_metric:
            readings_by_metric[m_type] = []
        readings_by_metric[m_type].append(r["value"])

    for metric_type, trend_res in trends.items():
        baseline = baselines.get(metric_type)
        recent_vals = readings_by_metric.get(metric_type, [])
        
        alert_info = evaluate_metric_alerts(
            area_id=area_id,
            metric_type=metric_type,
            trend=trend_res,
            baseline=baseline,
            recent_readings=recent_vals
        )
        
        if alert_info:
            severity = alert_info["severity"]
            message = alert_info["message"]
            
            # Check if this exact alert is already active (unacknowledged)
            cursor.execute(
                """
                SELECT id FROM alerts 
                WHERE area_id = ? AND metric_type = ? AND severity = ? AND message = ? AND acknowledged = 0
                """,
                (area_id, metric_type, severity, message)
            )
            existing = cursor.fetchone()
            
            if not existing:
                cursor.execute(
                    """
                    INSERT INTO alerts (area_id, metric_type, severity, message)
                    VALUES (?, ?, ?, ?)
                    """,
                    (area_id, metric_type, severity, message)
                )
                triggered_alerts.append({
                    "area_id": area_id,
                    "metric_type": metric_type,
                    "severity": severity,
                    "message": message
                })
                
    conn.commit()
    return triggered_alerts
