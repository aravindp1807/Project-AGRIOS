import React, { useEffect, useRef, useState } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import './MapView.css';

// CartoDB Dark Matter GL style - free, premium dark style requiring no API key
const BASEMAP_STYLE = 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json';

// Helper to construct a GeoJSON polygon representing a circle
function createCircleGeoJSON(centerLon, centerLat, radiusKm, points = 64) {
  const coords = [];
  const kmPerDegreeLat = 111.32;
  const kmPerDegreeLon = 111.32 * Math.cos((centerLat * Math.PI) / 180);

  for (let i = 0; i < points; i++) {
    const angle = (i * 2 * Math.PI) / points;
    const dx = radiusKm * Math.cos(angle);
    const dy = radiusKm * Math.sin(angle);

    const lon = centerLon + dx / kmPerDegreeLon;
    const lat = centerLat + dy / kmPerDegreeLat;
    coords.push([lon, lat]);
  }
  coords.push(coords[0]); // Close polygon

  return {
    type: 'Feature',
    geometry: {
      type: 'Polygon',
      coordinates: [coords]
    }
  };
}

export default function MapView({ aois, activeAoiId, selectedModes, onSelectAoi, onMapClick }) {
  const mapContainer = useRef(null);
  const map = useRef(null);
  const markersRef = useRef({});
  const [mapLoaded, setMapLoaded] = useState(false);
  const [basemap, setBasemap] = useState('original'); // 'original' | 'ocean' | 'satellite' | 'terrain'

  // Get active AOI object
  const activeAoi = aois.find((a) => a.id === activeAoiId);

  // Initialize Map
  useEffect(() => {
    if (map.current) return;

    map.current = new maplibregl.Map({
      container: mapContainer.current,
      style: BASEMAP_STYLE,
      center: [-98.5795, 39.8283], // Center on US
      zoom: 3.5,
      attributionControl: false
    });

    map.current.addControl(new maplibregl.NavigationControl(), 'top-right');

    map.current.on('load', () => {
      // 1. Add Satellite (Agriculture satellite basemap)
      map.current.addSource('basemap-satellite', {
        type: 'raster',
        tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'],
        tileSize: 256
      });
      map.current.addLayer({
        id: 'layer-basemap-satellite',
        type: 'raster',
        source: 'basemap-satellite',
        layout: { visibility: 'none' }
      });

      // 2. Add Ocean (Water Bodies highlighting basemap)
      map.current.addSource('basemap-ocean', {
        type: 'raster',
        tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}'],
        tileSize: 256
      });
      map.current.addLayer({
        id: 'layer-basemap-ocean',
        type: 'raster',
        source: 'basemap-ocean',
        layout: { visibility: 'none' }
      });

      // 3. Add Terrain (Contour topography basemap)
      map.current.addSource('basemap-terrain', {
        type: 'raster',
        tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}'],
        tileSize: 256
      });
      map.current.addLayer({
        id: 'layer-basemap-terrain',
        type: 'raster',
        source: 'basemap-terrain',
        layout: { visibility: 'none' }
      });

      setMapLoaded(true);
    });

    map.current.on('click', (e) => {
      if (onMapClick) {
        onMapClick(e.lngLat.lat, e.lngLat.lng);
      }
    });

    return () => {
      if (map.current) {
        map.current.remove();
        map.current = null;
      }
    };
  }, []);

  // Sync Basemap visibility
  useEffect(() => {
    if (!map.current || !mapLoaded) return;

    const basemapLayers = {
      satellite: 'layer-basemap-satellite',
      ocean: 'layer-basemap-ocean',
      terrain: 'layer-basemap-terrain'
    };

    Object.entries(basemapLayers).forEach(([key, layerId]) => {
      if (map.current.getLayer(layerId)) {
        const visibility = basemap === key ? 'visible' : 'none';
        map.current.setLayoutProperty(layerId, 'visibility', visibility);
      }
    });
  }, [basemap, mapLoaded]);

  // Sync Markers
  useEffect(() => {
    if (!map.current) return;

    // Remove obsolete markers
    Object.keys(markersRef.current).forEach((id) => {
      if (!aois.find((a) => a.id === id)) {
        markersRef.current[id].remove();
        delete markersRef.current[id];
      }
    });

    // Add or update markers
    aois.forEach((aoi) => {
      const isSelected = aoi.id === activeAoiId;
      
      if (markersRef.current[aoi.id]) {
        // Update styling of existing marker
        const el = markersRef.current[aoi.id].getElement();
        el.className = `custom-marker ${isSelected ? 'selected' : ''}`;
      } else {
        // Create new marker DOM element
        const el = document.createElement('div');
        el.className = `custom-marker ${isSelected ? 'selected' : ''}`;
        
        // Inside dot
        const dot = document.createElement('div');
        dot.className = 'marker-dot';
        el.appendChild(dot);

        // Click handler
        el.addEventListener('click', (e) => {
          e.stopPropagation();
          onSelectAoi(aoi.id);
        });

        // Add to map
        const marker = new maplibregl.Marker({ element: el })
          .setLngLat([aoi.longitude, aoi.latitude])
          .addTo(map.current);

        markersRef.current[aoi.id] = marker;
      }
    });
  }, [aois, activeAoiId, onSelectAoi]);

  // Sync Map center and radius overlay for active AOI
  useEffect(() => {
    if (!map.current || !mapLoaded) return;

    const sourceId = 'active-aoi-radius';
    const fillLayerId = 'active-aoi-radius-fill';
    const lineLayerId = 'active-aoi-radius-line';

    if (activeAoi) {
      // Fly to active location
      map.current.flyTo({
        center: [activeAoi.longitude, activeAoi.latitude],
        zoom: activeAoi.radius_km > 30 ? 8 : 10,
        essential: true,
        duration: 1500
      });

      // Generate circle GeoJSON
      const circleData = createCircleGeoJSON(activeAoi.longitude, activeAoi.latitude, activeAoi.radius_km);

      if (map.current.getSource(sourceId)) {
        map.current.getSource(sourceId).setData(circleData);
      } else {
        map.current.addSource(sourceId, {
          type: 'geojson',
          data: circleData
        });

        map.current.addLayer({
          id: fillLayerId,
          type: 'fill',
          source: sourceId,
          paint: {
            'fill-color': '#10b981',
            'fill-opacity': 0.12
          }
        });

        map.current.addLayer({
          id: lineLayerId,
          type: 'line',
          source: sourceId,
          paint: {
            'line-color': '#34d399',
            'line-width': 2,
            'line-dasharray': [2, 2]
          }
        });
      }
    } else {
      // Remove layer if no active AOI
      if (map.current.getLayer(fillLayerId)) map.current.removeLayer(fillLayerId);
      if (map.current.getLayer(lineLayerId)) map.current.removeLayer(lineLayerId);
      if (map.current.getSource(sourceId)) map.current.removeSource(sourceId);
    }
  }, [activeAoiId, mapLoaded]);

  // Sync NASA GIBS NDVI Raster Layer
  useEffect(() => {
    if (!map.current || !mapLoaded) return;

    const sourceId = 'nasa-gibs-ndvi';
    const layerId = 'nasa-gibs-ndvi-layer';

    const showVegetation = selectedModes.includes('vegetation');

    if (showVegetation) {
      if (!map.current.getSource(sourceId)) {
        // Construct date: yesterday (to ensure tiles have finished processing)
        const yesterday = new Date(Date.now() - 86400000);
        const dateStr = yesterday.toISOString().split('T')[0];
        
        map.current.addSource(sourceId, {
          type: 'raster',
          tiles: [
            `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_NDVI_8Day/default/${dateStr}/GoogleMapsCompatible_Level9/{z}/{y}/{x}.png`
          ],
          tileSize: 256
        });

        // Insert raster layer below labels but above basemap
        map.current.addLayer({
          id: layerId,
          type: 'raster',
          source: sourceId,
          paint: {
            'raster-opacity': 0.55
          }
        });
      }
    } else {
      // Remove vegetation layer if disabled
      if (map.current.getLayer(layerId)) map.current.removeLayer(layerId);
      if (map.current.getSource(sourceId)) map.current.removeSource(sourceId);
    }
  }, [selectedModes, mapLoaded]);

  return (
    <div className="map-view-wrapper">
      <div ref={mapContainer} className="map-canvas-container" />
      
      {/* Floating Basemap Selector */}
      <div className="basemap-selector glass-panel animate-fade-in">
        <button 
          className={`basemap-btn ${basemap === 'original' ? 'active' : ''}`}
          onClick={() => setBasemap('original')}
        >
          Original
        </button>
        <button 
          className={`basemap-btn ${basemap === 'ocean' ? 'active' : ''}`}
          onClick={() => setBasemap('ocean')}
        >
          Water Bodies
        </button>
        <button 
          className={`basemap-btn ${basemap === 'satellite' ? 'active' : ''}`}
          onClick={() => setBasemap('satellite')}
        >
          Agriculture
        </button>
        <button 
          className={`basemap-btn ${basemap === 'terrain' ? 'active' : ''}`}
          onClick={() => setBasemap('terrain')}
        >
          Terrain
        </button>
      </div>

      <div className="map-coordinates-legend">
        <span>MapLibre GL Engine</span>
        {activeAoi && (
          <span>
            {activeAoi.latitude.toFixed(4)}N, {activeAoi.longitude.toFixed(4)}W
          </span>
        )}
      </div>
    </div>
  );
}
