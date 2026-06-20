from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
import uuid
from db.connection import get_db

router = APIRouter(prefix="/aoi", tags=["Area of Interest"])

class AOICreate(BaseModel):
    name: str
    latitude: float
    longitude: float
    radius_km: Optional[float] = 10.0
    is_watched: Optional[bool] = False

class AOIUpdate(BaseModel):
    name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius_km: Optional[float] = None
    is_watched: Optional[bool] = None

class AOIResponse(BaseModel):
    id: str
    name: str
    latitude: float
    longitude: float
    radius_km: float
    is_watched: bool
    created_at: str
    alert_count: Optional[int] = 0

@router.post("", response_model=AOIResponse, status_code=status.HTTP_201_CREATED)
def create_aoi(aoi: AOICreate):
    aoi_id = str(uuid.uuid4())
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO areas_of_interest (id, name, latitude, longitude, radius_km, is_watched)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (aoi_id, aoi.name, aoi.latitude, aoi.longitude, aoi.radius_km, 1 if aoi.is_watched else 0)
        )
        
        cursor.execute(
            """
            SELECT id, name, latitude, longitude, radius_km, is_watched, created_at,
                   0 as alert_count
            FROM areas_of_interest WHERE id = ?
            """, 
            (aoi_id,)
        )
        row = cursor.fetchone()
        
    return {
        "id": row["id"],
        "name": row["name"],
        "latitude": row["latitude"],
        "longitude": row["longitude"],
        "radius_km": row["radius_km"],
        "is_watched": bool(row["is_watched"]),
        "created_at": row["created_at"],
        "alert_count": row["alert_count"]
    }

@router.get("", response_model=List[AOIResponse])
def list_aois():
    results = []
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, name, latitude, longitude, radius_km, is_watched, created_at,
                   (SELECT COUNT(*) FROM alerts WHERE area_id = id AND acknowledged = 0) as alert_count
            FROM areas_of_interest
            """
        )
        rows = cursor.fetchall()
        for row in rows:
            results.append({
                "id": row["id"],
                "name": row["name"],
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "radius_km": row["radius_km"],
                "is_watched": bool(row["is_watched"]),
                "created_at": row["created_at"],
                "alert_count": row["alert_count"]
            })
    return results

@router.get("/{aoi_id}", response_model=AOIResponse)
def get_aoi(aoi_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, name, latitude, longitude, radius_km, is_watched, created_at,
                   (SELECT COUNT(*) FROM alerts WHERE area_id = id AND acknowledged = 0) as alert_count
            FROM areas_of_interest WHERE id = ?
            """,
            (aoi_id,)
        )
        row = cursor.fetchone()
        
    if not row:
        raise HTTPException(status_code=404, detail="Area of Interest not found")
        
    return {
        "id": row["id"],
        "name": row["name"],
        "latitude": row["latitude"],
        "longitude": row["longitude"],
        "radius_km": row["radius_km"],
        "is_watched": bool(row["is_watched"]),
        "created_at": row["created_at"],
        "alert_count": row["alert_count"]
    }

@router.patch("/{aoi_id}", response_model=AOIResponse)
def update_aoi(aoi_id: str, aoi: AOIUpdate):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM areas_of_interest WHERE id = ?", (aoi_id,))
        existing = cursor.fetchone()
        
        if not existing:
            raise HTTPException(status_code=404, detail="Area of Interest not found")
            
        # Build update fields dynamically
        fields = []
        params = []
        
        if aoi.name is not None:
            fields.append("name = ?")
            params.append(aoi.name)
        if aoi.latitude is not None:
            fields.append("latitude = ?")
            params.append(aoi.latitude)
        if aoi.longitude is not None:
            fields.append("longitude = ?")
            params.append(aoi.longitude)
        if aoi.radius_km is not None:
            fields.append("radius_km = ?")
            params.append(aoi.radius_km)
        if aoi.is_watched is not None:
            fields.append("is_watched = ?")
            params.append(1 if aoi.is_watched else 0)
            
        if fields:
            query = f"UPDATE areas_of_interest SET {', '.join(fields)} WHERE id = ?"
            params.append(aoi_id)
            cursor.execute(query, tuple(params))
            
        cursor.execute(
            """
            SELECT id, name, latitude, longitude, radius_km, is_watched, created_at,
                   (SELECT COUNT(*) FROM alerts WHERE area_id = id AND acknowledged = 0) as alert_count
            FROM areas_of_interest WHERE id = ?
            """,
            (aoi_id,)
        )
        row = cursor.fetchone()
        
    return {
        "id": row["id"],
        "name": row["name"],
        "latitude": row["latitude"],
        "longitude": row["longitude"],
        "radius_km": row["radius_km"],
        "is_watched": bool(row["is_watched"]),
        "created_at": row["created_at"],
        "alert_count": row["alert_count"]
    }

@router.delete("/{aoi_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_aoi(aoi_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM areas_of_interest WHERE id = ?", (aoi_id,))
        existing = cursor.fetchone()
        
        if not existing:
            raise HTTPException(status_code=404, detail="Area of Interest not found")
            
        # Manually cascade delete dependent records to maintain absolute integrity
        cursor.execute("DELETE FROM readings WHERE area_id = ?", (aoi_id,))
        cursor.execute("DELETE FROM baselines WHERE area_id = ?", (aoi_id,))
        cursor.execute("DELETE FROM reports WHERE area_id = ?", (aoi_id,))
        cursor.execute("DELETE FROM alerts WHERE area_id = ?", (aoi_id,))
        cursor.execute("DELETE FROM collection_logs WHERE area_id = ?", (aoi_id,))
        
        # Finally delete AOI itself
        cursor.execute("DELETE FROM areas_of_interest WHERE id = ?", (aoi_id,))
        
    return
