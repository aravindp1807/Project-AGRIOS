# Agrios — Agricultural & Geospatial Resource Intelligence System

**Agrios** (Agricultural & Geospatial Resource Intelligence System) is a state-of-the-art open-source intelligence platform engineered to monitor, analyze, and report on agricultural and environmental resource telemetry. By integrating multi-spectral satellite overlays, ground-station hydrologic data, and agro-climate history, **agrios** provides farm managers, researchers, and environmental analysts with actionable intelligence for any user-defined geographic Area of Interest (AOI).

The platform is designed to operate seamlessly under two core paradigms:
1. **Search Mode (On-Demand Intelligence)**: Instantly query any latitude/longitude coordinate with a specified radius. The system fetches real-time and historical telemetry across climate, hydrology, and vegetation channels, generating an AI-synthesized intelligence report on the spot.
2. **Monitor Mode (Sustained Ingestion & Tracking)**: Transition selected AOIs to active tracking. A background worker periodically polls telemetry endpoints, updates baseline datasets, computes mathematical trend slopes, and triggers automated threshold alerts (Warning/Critical) upon detecting anomalies.

---

## 🚀 Key Features

*   **Unified Coordinate Ingestion**: Standardizes queries across global geographic inputs, translating latitude/longitude coordinates and custom search radii into precise API parameters for downstream providers.
*   **Time-Series Trend Detection**: Employs ordinary least squares (OLS) linear regression to calculate slope coefficients over historical data window sizes (e.g., 30-day, 90-day). This mathematically determines if metrics like temperature, precipitation, or water levels are `stable`, `rising`, or `falling`, providing a hard truth that prevents LLM hallucination of statistical trends.
*   **Tiered LLM Fallback Router**: Ensures maximum uptime for narrative generation by cycling through an prioritized pipeline of API providers:
    $$\text{OpenRouter (Llama 3.1 Nemotron)} \rightarrow \text{Google Gemini Flash} \rightarrow \text{Groq} \rightarrow \text{NVIDIA NIM} \rightarrow \text{Local Rule Engine}$$
    If all external LLM services fail or are unconfigured, the built-in rule engine synthesizes structured tabular summaries automatically.
*   **Multi-Select Intelligence Layers**: Overlay and visualizes diverse dataset vectors simultaneously:
    *   *Agro-Climate*: Daily temperature, precipitation, and solar irradiance.
    *   *Hydrology*: Streamflow discharge (cfs) and gauge height (ft) from the nearest active hydrological station.
    *   *Vegetation Health*: Dynamic MODIS Terra NDVI 8-day satellite raster tile overlays.
*   **Interactive MapLibre GL Map**: A premium, high-contrast dark GIS console featuring:
    *   Custom animated pulse/glow markers for selected locations.
    *   Geodesic search radius boundary circles drawn directly on the canvas.
    *   A dynamic basemap switcher (Satellite imagery, Oceanography, Topography, and Dark-matter vector tiles).
*   **Telemetry Visualization**: Responsive, glowing SVG area and line charts (built with Recharts) that detail historical curves, baseline averages, and statistical deviations.

---

## 🏗️ System Architecture & Technology Stack

The platform is decoupled into a high-performance backend microservice and a responsive, interactive client dashboard.

```
agrios Platform
├── Backend (FastAPI / Python 3.11+)
│   ├── Database Layer (SQLite / SQLAlchemy ORM)
│   ├── Worker Thread (APScheduler Scheduler)
│   ├── Ingestors (NASA POWER, Open-Meteo, USGS Water Services)
│   └── Analytics (OLS Linear Regression, Fallback LLM Router)
└── Frontend (React / MapLibre GL JS / Recharts)
```

| Component | Technology | Description |
|---|---|---|
| **Backend Framework** | Python 3.11+ / FastAPI | Asynchronous endpoint handlers, parallel remote requests, and automatic OpenAPI generation. |
| **Database** | SQLite | Serverless, zero-configuration SQL database for keeping historical readings and configs. |
| **Scheduler** | APScheduler | In-process background coordinator that executes scheduled telemetry syncs for watched AOIs. |
| **Map Engine** | MapLibre GL JS | GPU-accelerated vector map engine displaying geographic shapes and custom WMS/tile layers. |
| **Charts** | Recharts | Declarative, SVG-based React charts configured with custom tooltips, gradients, and reference lines. |

---

## 📥 Telemetry Data Sources

1.  **NASA POWER (Agro-Climatology)**:
    Provides daily meteorology data (temperature, precipitation, relative humidity, solar radiation) at a global $1/2^\circ \times 1/2^\circ$ resolution. *No API key required.*
2.  **Open-Meteo (Weather Forecasts & Archives)**:
    High-resolution grid point forecasts and historical weather archives to cross-reference short-term atmospheric developments. *No API key required.*
3.  **USGS Water Services (Hydrology)**:
    Fetches daily streamflow discharge ($ft^3/s$) and gauge height ($ft$) from the nearest active USGS monitoring station within the bounding area of interest (US locations only). *No API key required.*
4.  **NASA GIBS (NDVI Satellite Imagery)**:
    Renders MODIS Terra NDVI (Normalized Difference Vegetation Index) 8-day satellite raster tiles as visual layers overlayed directly onto the GIS map coordinates. *No API key required.*

---

## 🔧 Installation & Running Locally

### 1. Setup Backend
Navigate to the root directory and set up a virtual environment:
```bash
# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate  # On Windows
# source venv/bin/activate  # On macOS/Linux

# Install backend dependencies
pip install -r backend/requirements.txt
```

Create a `.env` file in the `backend/` directory and supply API keys (optional but recommended for LLM features):
```env
OPENROUTER_API_KEY=your-openrouter-key
GEMINI_API_KEY=your-gemini-key
GROQ_API_KEY=your-groq-key
NVIDIA_NIM_API_KEY=your-nvidia-nim-key
DATABASE_URL=sqlite:///./agrios.db
```
*Note: If no API keys are provided, the system falls back gracefully to its built-in rule-based summary generator, maintaining 100% functionality.*

Start the FastAPI application:
```bash
python -m uvicorn main:app --app-dir backend --reload --port 8000
```
The API Swagger documentation will be available at [http://localhost:8000/docs](http://localhost:8000/docs).

### 2. Setup Frontend
Navigate to the `frontend/` directory and install the Node packages:
```bash
cd frontend
npm install
npm run dev
```
The application will launch on your local dev server at [http://localhost:5173](http://localhost:5173).


---

## ☁️ Cloud Deployment

You can deploy **agrios** to the cloud for free using Render for the backend and Vercel for the frontend:

### 1. Deploy Backend (Render)
1. Sign up or log in to [Render.com](https://render.com).
2. Click **New +** and select **Blueprint**.
3. Connect your GitHub repository `Project-AGRIOS`.
4. Render will automatically detect the `render.yaml` configuration and set up the **agrios-backend** Web Service using Docker.
5. Provide your API keys (e.g. `GEMINI_API_KEY`, `OPENROUTER_API_KEY`, etc.) as environment variables in the Render dashboard.
6. Once deployed, copy your backend URL (e.g., `https://agrios-backend.onrender.com`).

### 2. Deploy Frontend (Vercel)
1. Sign up or log in to [Vercel.com](https://vercel.com).
2. Click **Add New** -> **Project** and import your `Project-AGRIOS` repository.
3. In the configuration settings:
   * Set **Root Directory** to `frontend`.
   * Add a new **Environment Variable**:
     * Key: `VITE_API_BASE_URL`
     * Value: Your Render backend URL (e.g. `https://agrios-backend.onrender.com`)
4. Click **Deploy**. Vercel will build and host your frontend.

---

## 🗃️ Database Schema

**agrios** organizes data using a clean, normalized relational structure:
*   `areas_of_interest`: Records registered name, coordinates (latitude, longitude), radius, and monitoring status.
*   `readings`: High-write table holding normalized daily telemetry readings (temperature, precipitation, soil moisture, discharge, gauge height).
*   `baselines`: Automatically computed rolling averages (30-day and 90-day) used to establish historic normalcy.
*   `reports`: Caches AI-synthesized narrative reports, tagging them with the LLM provider utilized.
*   `alerts`: Records warning and critical levels reached by telemetry triggers.
*   `collection_logs`: Diagnostic logger tracking background ingestion jobs and network status.
