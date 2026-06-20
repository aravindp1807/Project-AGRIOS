import React, { useState } from 'react';
import { Search, MapPin, Plus, Loader } from 'lucide-react';
import './AOISearch.css';

export default function AOISearch({ aois, activeAoiId, onSelectAoi, onCreateAoi, prefillCoords }) {
  const [isCreating, setIsCreating] = useState(false);
  const [name, setName] = useState('');
  const [lat, setLat] = useState('');
  const [lon, setLon] = useState('');
  const [radius, setRadius] = useState('10');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  // Automatically pre-fill coordinates when user clicks on map
  React.useEffect(() => {
    if (prefillCoords && prefillCoords.lat !== undefined && prefillCoords.lon !== undefined) {
      setLat(prefillCoords.lat.toFixed(6));
      setLon(prefillCoords.lon.toFixed(6));
      setIsCreating(true); // Switch to registration form
      setError('');
    }
  }, [prefillCoords]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    const latitude = parseFloat(lat);
    const longitude = parseFloat(lon);
    const radiusKm = parseFloat(radius);

    if (!name.trim()) return setError('Name is required');
    if (isNaN(latitude) || latitude < -90 || latitude > 90) return setError('Lat must be between -90 and 90');
    if (isNaN(longitude) || longitude < -180 || longitude > 180) return setError('Lon must be between -180 and 180');
    if (isNaN(radiusKm) || radiusKm <= 0) return setError('Radius must be positive');

    setSubmitting(true);
    try {
      await onCreateAoi({
        name,
        latitude,
        longitude,
        radius_km: radiusKm
      });
      setName('');
      setLat('');
      setLon('');
      setRadius('10');
      setIsCreating(false);
    } catch (err) {
      setError(err.message || 'Failed to create AOI');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="aoi-search-container glass-panel animate-fade-in">
      <div className="aoi-search-tabs">
        <button 
          className={`tab-btn ${!isCreating ? 'active' : ''}`}
          onClick={() => { setIsCreating(false); setError(''); }}
        >
          <Search size={14} /> Active Location
        </button>
        <button 
          className={`tab-btn ${isCreating ? 'active' : ''}`}
          onClick={() => { setIsCreating(true); setError(''); }}
        >
          <Plus size={14} /> Define Area
        </button>
      </div>

      {!isCreating ? (
        <div className="aoi-select-mode">
          <label>Select Monitored Area</label>
          {aois.length === 0 ? (
            <p className="empty-aoi-msg">No areas defined yet. Toggle "Define Area" to add one.</p>
          ) : (
            <div className="aoi-select-wrapper">
              <select 
                value={activeAoiId || ''} 
                onChange={(e) => onSelectAoi(e.target.value)}
                className="aoi-select"
              >
                <option value="" disabled>-- Select a Location --</option>
                {aois.map((aoi) => (
                  <option key={aoi.id} value={aoi.id}>
                    {aoi.name} ({aoi.latitude.toFixed(2)}, {aoi.longitude.toFixed(2)})
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="aoi-create-form">
          <div className="input-group">
            <label>Location Name</label>
            <input 
              type="text" 
              placeholder="e.g. Nebraska Wheat Zone" 
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={submitting}
              required
            />
          </div>
          <div className="coords-row">
            <div className="input-group">
              <label>Latitude</label>
              <input 
                type="number" 
                step="0.000001" 
                placeholder="40.81" 
                value={lat}
                onChange={(e) => setLat(e.target.value)}
                disabled={submitting}
                required
              />
            </div>
            <div className="input-group">
              <label>Longitude</label>
              <input 
                type="number" 
                step="0.000001" 
                placeholder="-96.70" 
                value={lon}
                onChange={(e) => setLon(e.target.value)}
                disabled={submitting}
                required
              />
            </div>
          </div>
          <div className="input-group">
            <label>Search Radius (km)</label>
            <input 
              type="number" 
              step="0.1" 
              value={radius}
              onChange={(e) => setRadius(e.target.value)}
              disabled={submitting}
              required
            />
          </div>

          {error && <div className="aoi-form-error">{error}</div>}

          <button type="submit" className="submit-btn" disabled={submitting}>
            {submitting ? <Loader className="spin" size={16} /> : <MapPin size={16} />}
            {submitting ? 'Registering...' : 'Register Location'}
          </button>
        </form>
      )}
    </div>
  );
}
