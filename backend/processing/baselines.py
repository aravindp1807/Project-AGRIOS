from typing import List, Optional
from datetime import datetime, timedelta

def compute_baseline(values: List[float]) -> Optional[float]:
    """Simple rolling average over the window."""
    if not values:
        return None
    return sum(values) / len(values)

def recompute_and_save_baseline(conn, area_id: str, metric_type: str, window_days: int) -> Optional[float]:
    """
    Fetches readings for the area_id and metric_type in the past window_days,
    computes the average baseline, and upserts it in the `baselines` table.
    """
    # Calculate cutoff date
    cutoff_date = (datetime.utcnow() - timedelta(days=window_days)).date()
    
    # Query readings
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT value FROM readings 
        WHERE area_id = ? AND metric_type = ? AND reading_date >= ?
        """,
        (area_id, metric_type, cutoff_date.isoformat())
    )
    rows = cursor.fetchall()
    values = [row["value"] for row in rows]
    
    avg_val = compute_baseline(values)
    if avg_val is None:
        return None
        
    # Upsert baseline in SQLite (requires SQLite 3.24.0+)
    cursor.execute(
        """
        INSERT INTO baselines (area_id, metric_type, window_days, avg_value, computed_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(area_id, metric_type, window_days) 
        DO UPDATE SET avg_value = excluded.avg_value, computed_at = excluded.computed_at
        """,
        (area_id, metric_type, window_days, avg_val)
    )
    conn.commit()
    return avg_val
