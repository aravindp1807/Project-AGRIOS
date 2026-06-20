import React, { useEffect, useState } from 'react';
import { ShieldAlert, Activity, RefreshCw } from 'lucide-react';
import MapView from './components/MapView';
import ModeToggle from './components/ModeToggle';
import AOISearch from './components/AOISearch';
import AOIReport from './components/AOIReport';
import WatchedAreasList from './components/WatchedAreasList';
import TrendChart from './components/TrendChart';
import './App.css';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || (
  window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost:8000'
    : `${window.location.protocol}//${window.location.hostname}:8000`
);


export default function App() {
  const [aois, setAois] = useState([]);
  const [activeAoiId, setActiveAoiId] = useState(null);
  const [selectedModes, setSelectedModes] = useState(['weather']);
  const [reportText, setReportText] = useState('');
  const [providerUsed, setProviderUsed] = useState('');
  const [readings, setReadings] = useState([]);
  const [prefillCoords, setPrefillCoords] = useState(null);
  
  const [loadingAois, setLoadingAois] = useState(true);
  const [searching, setSearching] = useState(false);

  // 1. Fetch all Areas of Interest on mount
  useEffect(() => {
    fetchAois();
  }, []);

  const fetchAois = async () => {
    setLoadingAois(true);
    try {
      const res = await fetch(`${API_BASE_URL}/aoi`);
      if (res.ok) {
        const data = await res.json();
        setAois(data);
        // Default to first location if none selected
        if (data.length > 0 && !activeAoiId) {
          setActiveAoiId(data[0].id);
        }
      }
    } catch (err) {
      console.error("Failed to load Areas of Interest:", err);
    } finally {
      setLoadingAois(false);
    }
  };

  // 2. Fetch intelligence report and readings when location changes
  useEffect(() => {
    if (activeAoiId) {
      executeSearch();
    }
  }, [activeAoiId]);

  const executeSearch = async () => {
    if (!activeAoiId) return;
    setSearching(true);
    try {
      const res = await fetch(`${API_BASE_URL}/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          area_id: activeAoiId,
          modes: selectedModes
        })
      });
      if (res.ok) {
        const data = await res.json();
        setReportText(data.report_text);
        setProviderUsed(data.provider_used);
        setReadings(data.readings);
      } else {
        const errData = await res.json();
        setReportText(`Error fetching report: ${errData.detail || 'Search execution failed.'}`);
        setReadings([]);
        setProviderUsed('system_error');
      }
    } catch (err) {
      console.error("Search API failed:", err);
      setReportText("Network error: Could not reach the AGRIOS backend server. Verify the server is running on localhost:8000.");
      setReadings([]);
      setProviderUsed('network_error');
    } finally {
      setSearching(false);
    }
  };

  // Callback to create a new AOI
  const handleCreateAoi = async (aoiData) => {
    const res = await fetch(`${API_BASE_URL}/aoi`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(aoiData)
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to create location');
    }
    const newAoi = await res.json();
    setAois((prev) => [...prev, newAoi]);
    setActiveAoiId(newAoi.id);
    setPrefillCoords(null); // Reset click position on successful registration
  };

  // Toggle watch status
  const handleToggleWatch = async (aoiId, isWatched) => {
    try {
      const res = await fetch(`${API_BASE_URL}/aoi/${aoiId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_watched: isWatched })
      });
      if (res.ok) {
        // Refresh local AOIs list
        await fetchAois();
      }
    } catch (err) {
      console.error("Failed to toggle watch status:", err);
    }
  };

  // Toggle modes
  const handleToggleMode = (modeId) => {
    setSelectedModes((prev) => {
      const next = prev.includes(modeId)
        ? prev.filter((m) => m !== modeId)
        : [...prev, modeId];
      // Keep at least one mode active
      return next.length > 0 ? next : prev;
    });
  };

  // Re-run search manually when mode selection is changed
  useEffect(() => {
    if (activeAoiId) {
      executeSearch();
    }
  }, [selectedModes]);

  const activeAoi = aois.find((a) => a.id === activeAoiId);

  return (
    <div className="app-container">
      {/* Map Background */}
      <div className="map-view-container">
        <MapView
          aois={aois}
          activeAoiId={activeAoiId}
          selectedModes={selectedModes}
          onSelectAoi={setActiveAoiId}
          onMapClick={(lat, lon) => setPrefillCoords({ lat, lon })}
        />
      </div>

      {/* Left Toolbar (Sidebar) */}
      <div className="left-sidebar">
        <div className="app-header glass-panel animate-fade-in">
          <div className="brand-logo">
            <Activity size={24} color="#10b981" />
            <h1>AGRIOS</h1>
          </div>
          <span className="brand-subtitle">Resource Intelligence System</span>
        </div>

        <AOISearch
          aois={aois}
          activeAoiId={activeAoiId}
          onSelectAoi={setActiveAoiId}
          onCreateAoi={handleCreateAoi}
          prefillCoords={prefillCoords}
        />

        <ModeToggle
          selectedModes={selectedModes}
          onToggleMode={handleToggleMode}
        />

        <WatchedAreasList
          aois={aois}
          activeAoiId={activeAoiId}
          onSelectAoi={setActiveAoiId}
          onToggleWatch={handleToggleWatch}
        />
      </div>

      {/* Right Intelligence Panel */}
      <div className="right-panel">
        <div className="right-panel-content animate-fade-in-right">
          <AOIReport
            aoi={activeAoi}
            reportText={reportText}
            providerUsed={providerUsed}
            readings={readings}
            onRefresh={executeSearch}
            refreshing={searching}
            selectedModes={selectedModes}
          />

          {readings.length > 0 && (
            <TrendChart readings={readings} />
          )}
        </div>
      </div>
    </div>
  );
}
