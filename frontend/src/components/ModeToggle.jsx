import React from 'react';
import { CloudSun, Droplet, Leaf, Satellite } from 'lucide-react';
import './ModeToggle.css';

const MODE_DETAILS = [
  { id: 'weather', label: 'Agro-Climate', icon: CloudSun, color: '#3b82f6', desc: 'Temp, Precip, Solar' },
  { id: 'water', label: 'Hydrology', icon: Droplet, color: '#06b6d4', desc: 'Discharge, Gauge Height' },
  { id: 'vegetation', label: 'Vegetation Health', icon: Leaf, color: '#10b981', desc: 'NASA GIBS NDVI Tiles' }
];

export default function ModeToggle({ selectedModes, onToggleMode }) {
  return (
    <div className="mode-toggle-container glass-panel animate-fade-in">
      <div className="mode-toggle-header">
        <h3>Select Intelligence Modes</h3>
        <p>Combine multiple data overlays</p>
      </div>
      <div className="mode-toggle-grid">
        {MODE_DETAILS.map((mode) => {
          const Icon = mode.icon;
          const isActive = selectedModes.includes(mode.id);
          return (
            <button
              key={mode.id}
              className={`mode-btn ${isActive ? 'active' : ''}`}
              onClick={() => onToggleMode(mode.id)}
              style={{
                '--mode-color': mode.color,
                borderColor: isActive ? mode.color : 'rgba(255,255,255,0.08)'
              }}
            >
              <div className="mode-btn-content">
                <div className="icon-wrapper" style={{ backgroundColor: isActive ? `${mode.color}22` : 'rgba(255,255,255,0.03)' }}>
                  <Icon size={20} color={isActive ? mode.color : '#9ca3af'} />
                </div>
                <div className="mode-info">
                  <span className="mode-label">{mode.label}</span>
                  <span className="mode-desc">{mode.desc}</span>
                </div>
              </div>
              {isActive && <div className="glow-indicator" style={{ backgroundColor: mode.color }} />}
            </button>
          );
        })}
      </div>
    </div>
  );
}
