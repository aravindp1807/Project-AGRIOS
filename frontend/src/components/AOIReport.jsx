import React from 'react';
import { 
  Thermometer, 
  CloudRain, 
  Sun, 
  Waves, 
  Ruler, 
  TrendingUp, 
  TrendingDown, 
  Minus, 
  AlertTriangle, 
  CheckCircle2, 
  RefreshCw,
  Cpu,
  Droplet
} from 'lucide-react';
import './AOIReport.css';

// Map metric types to Icons
const METRIC_CONFIG = {
  temperature: { label: 'Temperature', icon: Thermometer, color: '#f59e0b', defaultUnit: 'C' },
  precipitation: { label: 'Precipitation', icon: CloudRain, color: '#3b82f6', defaultUnit: 'mm' },
  solar_radiation: { label: 'Solar Radiation', icon: Sun, color: '#eab308', defaultUnit: 'MJ/m²' },
  water_discharge: { label: 'Water Discharge', icon: Waves, color: '#06b6d4', defaultUnit: 'cfs' },
  gauge_height: { label: 'Gauge Height', icon: Ruler, color: '#a855f7', defaultUnit: 'ft' },
  soil_moisture: { label: 'Soil Moisture', icon: Droplet, color: '#10b981', defaultUnit: 'm³/m³' }
};

// Lightweight inline markdown helper to support bolding, lists, and headers in React 19
const renderMarkdown = (text) => {
  if (!text) return null;
  const lines = text.split('\n');
  
  const parseBold = (str) => {
    const parts = str.split('**');
    return parts.map((part, i) => i % 2 === 1 ? <strong key={i}>{part}</strong> : part);
  };

  return lines.map((line, idx) => {
    const trimmed = line.trim();
    if (trimmed.startsWith('###')) {
      return <h4 key={idx}>{parseBold(trimmed.substring(3).trim())}</h4>;
    }
    if (trimmed.startsWith('##')) {
      return <h3 key={idx}>{parseBold(trimmed.substring(2).trim())}</h3>;
    }
    if (trimmed.startsWith('#')) {
      return <h2 key={idx}>{parseBold(trimmed.substring(1).trim())}</h2>;
    }
    if (trimmed.startsWith('-') || trimmed.startsWith('*')) {
      return <li key={idx}>{parseBold(trimmed.substring(1).trim())}</li>;
    }
    if (!trimmed) {
      return <div key={idx} style={{ height: '8px' }} />;
    }
    return <p key={idx}>{parseBold(trimmed)}</p>;
  });
};

export default function AOIReport({ 
  aoi, 
  reportText, 
  providerUsed, 
  readings, 
  onRefresh, 
  refreshing,
  selectedModes = []
}) {
  if (!aoi) {
    return (
      <div className="aoi-report-empty glass-panel animate-fade-in">
        <Cpu size={32} color="#9ca3af" />
        <p>No location selected. Choose an Area of Interest above to load intelligence reports.</p>
      </div>
    );
  }

  // Get unique latest readings per metric type
  const latestMetrics = {};
  readings.forEach((r) => {
    if (!latestMetrics[r.metric_type]) {
      latestMetrics[r.metric_type] = r;
    }
  });

  const waterModeActive = selectedModes.includes('water');
  const hasWaterReadings = !!(latestMetrics.water_discharge || latestMetrics.gauge_height);

  // Simple local calculations of deviations if not computed on backend
  const metricCards = Object.entries(latestMetrics).map(([metric_type, r]) => {
    const config = METRIC_CONFIG[metric_type] || { label: metric_type, icon: Sun, color: '#6b7280' };
    const Icon = config.icon;
    
    // We'll calculate a local 30-day baseline to display in case it is needed, 
    // but the backend provides it. In our readings list we just have the raw values.
    // For this UI card, we show the current value and trend.
    return (
      <div key={metric_type} className="metric-card" style={{ '--card-border': config.color }}>
        <div className="metric-card-header">
          <div className="metric-icon-box" style={{ backgroundColor: `${config.color}22` }}>
            <Icon size={18} color={config.color} />
          </div>
          <span className="metric-title">{config.label}</span>
        </div>
        <div className="metric-value-box">
          <span className="metric-val">{r.value.toFixed(1)}</span>
          <span className="metric-unit">{r.unit}</span>
        </div>
        <div className="metric-source-tag">Source: {r.source.replace('_', ' ').toUpperCase()}</div>
      </div>
    );
  });

  return (
    <div className="aoi-report-container glass-panel animate-fade-in">
      <div className="report-header">
        <div>
          <h2>{aoi.name}</h2>
          <p className="coords-sub">Center: {aoi.latitude.toFixed(4)}, {aoi.longitude.toFixed(4)} • Radius: {aoi.radius_km}km</p>
        </div>
        
        <button 
          className={`refresh-report-btn ${refreshing ? 'spinning' : ''}`}
          onClick={onRefresh}
          disabled={refreshing}
          title="Re-run API fetches & synthesis"
        >
          <RefreshCw size={14} />
          {refreshing ? 'Synthesizing...' : 'Re-Run Intel'}
        </button>
      </div>

      <div className="report-section-divider" />

      {/* Synthesis Text Card */}
      <div className="ai-synthesis-card">
        <div className="ai-synthesis-header">
          <div className="ai-badge">
            <Cpu size={14} /> AI Synthesis Report
          </div>
          <span className="provider-tag">Model: {providerUsed.replace('_', ' ')}</span>
        </div>
        <div className="ai-synthesis-content">
          {refreshing ? (
            <div className="report-loading-placeholder">
              <RefreshCw className="spin-loading" size={24} />
              <p>Fetching active telemetry and compiling rolling statistical trends...</p>
            </div>
          ) : (
            renderMarkdown(reportText)
          )}
        </div>
      </div>

      {/* Metrics Section */}
      <div className="metrics-section">
        <h3>Current Site Metrics</h3>
        <p className="section-sub">Latest values fetched from telemetry sources</p>
        
        {waterModeActive && !hasWaterReadings && (
          <div className="water-warning-card">
            <AlertTriangle size={18} color="#f59e0b" style={{ flexShrink: 0 }} />
            <div className="water-warning-content">
              <span>Hydrology Telemetry Unavailable</span>
              <p>USGS water body data is restricted to US coverage. Coordinates outside the US will show no discharge/gauge readings.</p>
            </div>
          </div>
        )}
        
        {metricCards.length === 0 ? (
          <div className="empty-metrics-msg">
            No numeric readings fetched yet. Click "Re-Run Intel" to start ingestion.
          </div>
        ) : (
          <div className="metrics-grid">
            {metricCards}
          </div>
        )}
      </div>
    </div>
  );
}
