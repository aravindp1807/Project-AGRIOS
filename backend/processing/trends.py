from dataclasses import dataclass
from typing import List, Tuple, Optional
from datetime import datetime, timedelta

@dataclass
class TrendResult:
    slope: float
    direction: str         # 'rising' | 'falling' | 'stable'
    deviation_pct: float   # deviation of latest value from 30-day baseline

def calculate_linear_regression(x: List[float], y: List[float]) -> float:
    """Computes the slope of the linear regression line for x and y."""
    n = len(x)
    if n < 2:
        return 0.0
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    num = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
    den = sum((x[i] - mean_x) ** 2 for i in range(n))
    if den == 0:
        return 0.0
    return num / den

def detect_trend(readings: List[Tuple[datetime.date, float]], baseline: Optional[float] = None) -> Optional[TrendResult]:
    """
    Computes linear regression slope over the reading series.
    Returns: TrendResult with direction ('rising'|'falling'|'stable'), slope, 
             deviation_pct (latest value vs 30-day baseline).
    Threshold for 'stable' vs directional: slope within +/-2% of mean = stable.
    """
    if not readings:
        return None
        
    # Sort readings chronologically
    sorted_readings = sorted(readings, key=lambda x: x[0])
    
    # Calculate days relative to the first reading date
    start_date = sorted_readings[0][0]
    x = [(r[0] - start_date).days for r in sorted_readings]
    y = [r[1] for r in sorted_readings]
    
    n = len(sorted_readings)
    if n == 0:
        return None
        
    slope = calculate_linear_regression(x, y)
    mean_y = sum(y) / n
    
    # Determine direction based on slope vs +/- 2% of the mean value
    mean_threshold = abs(0.02 * mean_y)
    if abs(slope) <= mean_threshold:
        direction = "stable"
    elif slope > mean_threshold:
        direction = "rising"
    else:
        direction = "falling"
        
    # Calculate deviation percentage of the latest reading vs the baseline
    latest_val = sorted_readings[-1][1]
    
    # Fallback: if baseline is not provided, use the mean of the readings
    effective_baseline = baseline if baseline is not None else mean_y
    
    if effective_baseline is not None and effective_baseline != 0:
        deviation_pct = ((latest_val - effective_baseline) / effective_baseline) * 100
    else:
        deviation_pct = 0.0
        
    return TrendResult(
        slope=slope,
        direction=direction,
        deviation_pct=deviation_pct
    )

def detect_trend_for_area_metric(conn, area_id: str, metric_type: str) -> Optional[TrendResult]:
    """
    Fetches the last 30 days of readings and the 30-day baseline for an area and metric,
    then computes and returns the TrendResult.
    """
    # 30-day date cutoff
    cutoff_date = (datetime.utcnow() - timedelta(days=30)).date()
    
    # Fetch readings
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT reading_date, value FROM readings 
        WHERE area_id = ? AND metric_type = ? AND reading_date >= ?
        ORDER BY reading_date ASC
        """,
        (area_id, metric_type, cutoff_date.isoformat())
    )
    rows = cursor.fetchall()
    
    # Parse reading_date string to datetime.date
    readings = []
    for r in rows:
        try:
            d = datetime.strptime(r["reading_date"], "%Y-%m-%d").date()
            readings.append((d, r["value"]))
        except ValueError:
            continue
            
    if len(readings) < 2:
        # Not enough readings to compute a trend
        return None
        
    # Fetch 30-day baseline
    cursor.execute(
        """
        SELECT avg_value FROM baselines 
        WHERE area_id = ? AND metric_type = ? AND window_days = 30
        """,
        (area_id, metric_type)
    )
    baseline_row = cursor.fetchone()
    baseline = baseline_row["avg_value"] if baseline_row else None
    
    return detect_trend(readings, baseline)
