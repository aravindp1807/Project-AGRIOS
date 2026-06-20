import React, { useState } from 'react';
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer 
} from 'recharts';
import { TrendingUp, Activity } from 'lucide-react';
import './TrendChart.css';

const CHART_CONFIGS = {
  temperature: { label: 'Temperature History', stroke: '#f59e0b', fill: 'url(#tempGrad)', unit: 'C' },
  precipitation: { label: 'Precipitation History', stroke: '#3b82f6', fill: 'url(#precipGrad)', unit: 'mm' },
  solar_radiation: { label: 'Solar Radiation History', stroke: '#eab308', fill: 'url(#solarGrad)', unit: 'MJ/m²' },
  water_discharge: { label: 'Water Discharge History', stroke: '#06b6d4', fill: 'url(#dischargeGrad)', unit: 'cfs' },
  gauge_height: { label: 'Gauge Height History', stroke: '#a855f7', fill: 'url(#gaugeGrad)', unit: 'ft' },
  soil_moisture: { label: 'Soil Moisture History', stroke: '#10b981', fill: 'url(#defaultGrad)', unit: 'm³/m³' }
};

export default function TrendChart({ readings }) {
  // 1. Group readings by metric type
  const readingsByMetric = {};
  readings.forEach((r) => {
    if (!readingsByMetric[r.metric_type]) {
      readingsByMetric[r.metric_type] = [];
    }
    readingsByMetric[r.metric_type].push(r);
  });

  const availableMetrics = Object.keys(readingsByMetric);
  const [selectedMetric, setSelectedMetric] = useState(availableMetrics[0] || '');

  // Keep state updated if selectedMetric is no longer available or not set
  React.useEffect(() => {
    if (availableMetrics.length > 0 && (!selectedMetric || !availableMetrics.includes(selectedMetric))) {
      setSelectedMetric(availableMetrics[0]);
    }
  }, [readings]);

  if (availableMetrics.length === 0) {
    return null;
  }

  // Filter and sort readings for chart chronologically (date ascending)
  const chartData = [...(readingsByMetric[selectedMetric] || [])]
    .map(r => ({
      date: r.reading_date,
      value: r.value,
      // Format readable date for tooltip/axis
      formattedDate: new Date(r.reading_date).toLocaleDateString(undefined, {month: 'short', day: 'numeric'})
    }))
    .reverse(); // Backend returns descending, reverse for chronological chart

  const config = CHART_CONFIGS[selectedMetric] || { label: selectedMetric, stroke: '#10b981', fill: 'url(#defaultGrad)', unit: '' };

  return (
    <div className="trend-chart-container glass-panel animate-fade-in">
      <div className="chart-header">
        <div className="chart-title">
          <TrendingUp size={16} color={config.stroke} />
          <h3>Historical Trends</h3>
        </div>
        
        {availableMetrics.length > 1 && (
          <select 
            value={selectedMetric} 
            onChange={(e) => setSelectedMetric(e.target.value)}
            className="metric-select-dropdown"
            style={{ borderColor: config.stroke }}
          >
            {availableMetrics.map(m => (
              <option key={m} value={m}>
                {m.replace('_', ' ').toUpperCase()}
              </option>
            ))}
          </select>
        )}
      </div>

      <div className="chart-wrapper">
        {chartData.length < 2 ? (
          <div className="chart-empty-msg">
            <Activity size={24} color="#6b7280" />
            <p>Not enough historical points to plot trend line. Keep polling to build data history.</p>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={160}>
            <AreaChart data={chartData} margin={{ top: 10, right: 5, left: -25, bottom: 0 }}>
              <defs>
                <linearGradient id="tempGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#f59e0b" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="precipGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="solarGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#eab308" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#eab308" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="dischargeGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#06b6d4" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="gaugeGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#a855f7" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#a855f7" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="defaultGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" vertical={false} />
              <XAxis 
                dataKey="formattedDate" 
                tick={{fontSize: 9, fill: '#6b7280'}} 
                axisLine={false} 
                tickLine={false} 
              />
              <YAxis 
                tick={{fontSize: 9, fill: '#6b7280'}} 
                axisLine={false} 
                tickLine={false} 
                domain={['auto', 'auto']}
              />
              <Tooltip 
                contentStyle={{backgroundColor: '#111827', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '6px'}}
                labelStyle={{fontSize: 10, color: '#9ca3af', fontWeight: 600}}
                itemStyle={{fontSize: 12, color: config.stroke}}
                formatter={(value) => [`${value.toFixed(1)} ${config.unit}`, 'Value']}
              />
              <Area 
                type="monotone" 
                dataKey="value" 
                stroke={config.stroke} 
                strokeWidth={2}
                fill={config.fill} 
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
