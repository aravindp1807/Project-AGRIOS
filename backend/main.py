from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from db.connection import init_db
from api.routes_aoi import router as aoi_router
from api.routes_search import router as search_router
from api.routes_monitor import router as monitor_router
from api.routes_map import router as map_router

# Ensure the database file is created and the schema is applied on startup
print("Initializing database...")
init_db()

app = FastAPI(
    title="AGRIOS API", 
    description="Agricultural & Geospatial Resource Intelligence System",
    version="1.0.0"
)

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(aoi_router)
app.include_router(search_router)
app.include_router(monitor_router)
app.include_router(map_router)

@app.on_event("startup")
def start_scheduler():
    """Starts background monitor scheduler if implemented."""
    try:
        from scheduler.monitor_job import start_monitor_scheduler
        start_monitor_scheduler()
        print("Background monitor scheduler started successfully.")
    except ImportError:
        print("Background monitor scheduler module not implemented yet. Skipping startup.")
    except Exception as e:
        print(f"Failed to start background monitor scheduler: {e}")

@app.get("/")
def read_root():
    return {
        "status": "AGRIOS API is running",
        "system": "AGRIOS",
        "version": "1.0.0",
        "description": "Agricultural & Geospatial Resource Intelligence System"
    }
