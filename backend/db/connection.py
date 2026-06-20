import sqlite3
import os
from contextlib import contextmanager

# Parse DATABASE_URL from environment or fallback
db_url = os.getenv("DATABASE_URL", "sqlite:///./agrios.db")
if db_url.startswith("sqlite:///"):
    DB_FILE = db_url[10:]
elif db_url.startswith("sqlite://"):
    DB_FILE = db_url[9:]
else:
    DB_FILE = db_url

def init_db():
    """Initializes the database schema if tables don't exist."""
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    # Ensure directory containing DB exists
    db_dir = os.path.dirname(os.path.abspath(DB_FILE))
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
        
    with sqlite3.connect(DB_FILE) as conn:
        with open(schema_path, "r") as f:
            conn.executescript(f.read())
        conn.commit()
    print(f"Database initialized at {DB_FILE}")

@contextmanager
def get_db():
    """Context manager yielding a SQLite connection with dictionary row access and foreign keys enabled."""
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
