import React from 'react';
import { Eye, EyeOff, Bell, Star } from 'lucide-react';
import './WatchedAreasList.css';

export default function WatchedAreasList({ aois, activeAoiId, onSelectAoi, onToggleWatch }) {
  const watchedAois = aois.filter(a => a.is_watched);

  return (
    <div className="watched-areas-container glass-panel animate-fade-in">
      <div className="watched-areas-header">
        <div className="watched-title-row">
          <Eye size={16} color="#10b981" />
          <h3>Watched Locations</h3>
        </div>
        <p>Background polling & alert tracking</p>
      </div>

      <div className="watched-areas-list">
        {watchedAois.length === 0 ? (
          <div className="empty-watched-msg">
            <p>You are not monitoring any locations yet.</p>
            <p className="subtext">Register a location and click the star icon to toggle watch mode.</p>
          </div>
        ) : (
          watchedAois.map((aoi) => {
            const isActive = aoi.id === activeAoiId;
            const hasAlerts = aoi.alert_count > 0;
            
            return (
              <div 
                key={aoi.id} 
                className={`watched-item ${isActive ? 'active' : ''}`}
                onClick={() => onSelectAoi(aoi.id)}
              >
                <div className="watched-item-main">
                  <span className="watched-name">{aoi.name}</span>
                  <span className="watched-coords">
                    {aoi.latitude.toFixed(2)}N, {aoi.longitude.toFixed(2)}W
                  </span>
                </div>
                
                <div className="watched-actions" onClick={(e) => e.stopPropagation()}>
                  {hasAlerts && (
                    <div className="alert-badge animate-pulse">
                      <Bell size={10} />
                      <span>{aoi.alert_count}</span>
                    </div>
                  )}
                  
                  <button 
                    className="unwatch-btn watched"
                    onClick={() => onToggleWatch(aoi.id, false)}
                    title="Stop monitoring this location"
                  >
                    <Star size={14} fill="#fbbf24" color="#fbbf24" />
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Non-watched areas shortcut list */}
      {aois.filter(a => !a.is_watched).length > 0 && (
        <div className="unmonitored-shortcuts">
          <h4>Other Locations</h4>
          <div className="shortcut-grid">
            {aois.filter(a => !a.is_watched).map(aoi => (
              <button 
                key={aoi.id} 
                className="shortcut-tag-btn"
                onClick={() => onToggleWatch(aoi.id, true)}
                title="Start monitoring"
              >
                <Star size={10} style={{ marginRight: '4px' }} />
                {aoi.name}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
