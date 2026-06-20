from fastapi import APIRouter
from datetime import datetime, timedelta
from ingestion.nasa_gibs import get_gibs_tile_url

router = APIRouter(prefix="/map", tags=["Map Overlays"])

@router.get("/gibs-tile-url")
def get_nasa_gibs_tile_url(layer: str = "MODIS_Terra_NDVI_8Day", date: str = None):
    """
    Returns the templated tile URL for NASA GIBS WMTS raster overlay.
    Defaults to yesterday's date if none provided to ensure tile rendering availability.
    """
    if not date:
        yesterday = datetime.utcnow() - timedelta(days=1)
        date = yesterday.strftime("%Y-%m-%d")
        
    url = get_gibs_tile_url(layer, date)
    return {"url_template": url}
