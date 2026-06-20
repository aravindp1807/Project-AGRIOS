from backend.database import engine, Base, SessionLocal
from backend.ingestion import poll_nasa_apis_sync
from backend import models

# Create tables if they don't exist
print("Creating database tables...")
Base.metadata.create_all(bind=engine)

# Run ingestion
print("Running initial ingestion...")
db = SessionLocal()
try:
    poll_nasa_apis_sync(db)
    
    # Check what we got
    donki_count = db.query(models.DonkiEvent).count()
    eonet_count = db.query(models.EonetEvent).count()
    print(f"Ingestion successful! Database now has {donki_count} DONKI events and {eonet_count} EONET events.")
finally:
    db.close()
