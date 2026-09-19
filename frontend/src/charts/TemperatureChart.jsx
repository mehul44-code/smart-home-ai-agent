import React from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine
} from 'recharts';

export function TemperatureChart({ data = [], targetTemp = 22.0 }) {
  const chartData = data.map((d) => ({
    ...d,
    time: d.timestamp ? new Date(d.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''
  }));

  return (
    <div className="glass-card" style={{ padding: '1.25rem' }}>
      <h3 style={{ fontSize: '0.95rem', fontWeight: '600', marginBottom: '1rem' }}>
        Thermodynamic Temperature Tracking (°C)
      </h3>
      <div style={{ width: '100%', height: 240 }}>
        {chartData.length === 0 ? (
          <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)' }}>
            Awaiting telemetry data...
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="time" stroke="#64748b" fontSize={11} />
              <YAxis stroke="#64748b" domain={['auto', 'auto']} fontSize={11} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#111827',
                  borderColor: 'rgba(255,255,255,0.1)',
                  borderRadius: '8px',
                  fontSize: '12px'
                }}
              />
              <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
              <ReferenceLine y={targetTemp} stroke="#a855f7" strokeDasharray="3 3" label={{ value: 'Target', fill: '#c084fc', fontSize: 10 }} />
              <Line type="monotone" dataKey="indoor_temp_c" name="Indoor Temp (°C)" stroke="#06b6d4" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="outdoor_temp_c" name="Outdoor Temp (°C)" stroke="#f43f5e" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
