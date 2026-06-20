from dataclasses import dataclass
from datetime import date, datetime
from typing import Union, List

# Allowed sources and metrics as defined by schema & requirements
VALID_SOURCES = {"nasa_power", "open_meteo", "usgs_water"}
VALID_METRICS = {
    "temperature",
    "precipitation",
    "solar_radiation",
    "water_discharge",
    "gauge_height",
    "soil_moisture",
}

@dataclass
class IngestionResult:
    area_id: str
    source: str
    metric_type: str
    value: float
    unit: str
    reading_date: date  # python datetime.date

def normalize_reading(
    area_id: str,
    source: str,
    metric_type: str,
    value: Union[float, int, str],
    unit: str,
    reading_date: Union[date, datetime, str]
) -> IngestionResult:
    """
    Validates and normalizes raw reading values and dates.
    Raises ValueError if input data is invalid.
    """
    if source not in VALID_SOURCES:
        raise ValueError(f"Invalid source: {source}. Must be one of {VALID_SOURCES}")
        
    if metric_type not in VALID_METRICS:
        raise ValueError(f"Invalid metric_type: {metric_type}. Must be one of {VALID_METRICS}")
        
    # Normalize value to float
    try:
        norm_value = float(value)
    except (TypeError, ValueError) as e:
        raise ValueError(f"Invalid reading value: {value}. Must be numeric.") from e
        
    # Normalize date
    if isinstance(reading_date, str):
        # Support YYYY-MM-DD or YYYYMMDD
        reading_date = reading_date.strip()
        try:
            if "-" in reading_date:
                norm_date = datetime.strptime(reading_date[:10], "%Y-%m-%d").date()
            else:
                norm_date = datetime.strptime(reading_date[:8], "%Y%m%d").date()
        except ValueError as e:
            raise ValueError(f"Invalid reading date format: {reading_date}. Must be YYYY-MM-DD or YYYYMMDD.") from e
    elif isinstance(reading_date, datetime):
        norm_date = reading_date.date()
    elif isinstance(reading_date, date):
        norm_date = reading_date
    else:
        raise ValueError(f"Unsupported reading_date type: {type(reading_date)}")
        
    return IngestionResult(
        area_id=area_id,
        source=source,
        metric_type=metric_type,
        value=norm_value,
        unit=unit,
        reading_date=norm_date
    )
