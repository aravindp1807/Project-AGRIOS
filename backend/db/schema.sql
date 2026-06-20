-- Areas of Interest: the core object everything else attaches to
CREATE TABLE IF NOT EXISTS areas_of_interest (
    id TEXT PRIMARY KEY,              -- UUID
    name TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    radius_km REAL DEFAULT 10,        -- for bounding-box queries (e.g. USGS site lookup)
    is_watched BOOLEAN DEFAULT 0,     -- true = monitor mode active
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Normalized time-series readings from all numeric sources
CREATE TABLE IF NOT EXISTS readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    area_id TEXT NOT NULL REFERENCES areas_of_interest(id),
    source TEXT NOT NULL,             -- 'nasa_power' | 'open_meteo' | 'usgs_water'
    metric_type TEXT NOT NULL,        -- 'temperature' | 'precipitation' | 'solar_radiation' | 'water_discharge' | 'gauge_height'
    value REAL NOT NULL,
    unit TEXT NOT NULL,
    reading_date DATE NOT NULL,       -- the date the reading represents (not fetch time)
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(area_id, source, metric_type, reading_date)
);

CREATE INDEX IF NOT EXISTS idx_readings_lookup ON readings(area_id, metric_type, reading_date);

-- Computed rolling baselines per area/metric
CREATE TABLE IF NOT EXISTS baselines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    area_id TEXT NOT NULL REFERENCES areas_of_interest(id),
    metric_type TEXT NOT NULL,
    window_days INTEGER NOT NULL,     -- 30 or 90
    avg_value REAL NOT NULL,
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(area_id, metric_type, window_days)
);

-- Collection logs for debugging flaky sources
CREATE TABLE IF NOT EXISTS collection_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    area_id TEXT REFERENCES areas_of_interest(id),
    source TEXT NOT NULL,
    status TEXT NOT NULL,             -- 'success' | 'error'
    error_message TEXT,
    response_time_ms INTEGER,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- AI-generated synthesis reports (cached, since LLM calls cost time/quota)
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    area_id TEXT NOT NULL REFERENCES areas_of_interest(id),
    report_text TEXT NOT NULL,
    modes_included TEXT NOT NULL,     -- JSON array, e.g. '["weather","water"]'
    llm_provider_used TEXT NOT NULL,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Alerts for watched areas
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    area_id TEXT NOT NULL REFERENCES areas_of_interest(id),
    metric_type TEXT NOT NULL,
    severity TEXT NOT NULL,           -- 'info' | 'warning' | 'critical'
    message TEXT NOT NULL,
    triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    acknowledged BOOLEAN DEFAULT 0
);
