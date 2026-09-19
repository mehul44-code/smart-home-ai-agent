import React from 'react';
import { Power, Flame, BatteryCharging, Wind, Layers } from 'lucide-react';

export function ApplianceCard({ appliances = {}, onOverride }) {
  const getIcon = (category) => {
    switch (category) {
      case 'HVAC':
        return <Wind size={18} color="var(--accent-cyan)" />;
      case 'WATER_HEATER':
        return <Flame size={18} color="var(--accent-amber)" />;
      case 'EV':
        return <BatteryCharging size={18} color="var(--accent-emerald)" />;
      default:
        return <Layers size={18} color="var(--accent-blue)" />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'ON':
        return 'var(--accent-emerald)';
      case 'ECO':
        return 'var(--accent-cyan)';
      case 'OFF':
      default:
        return 'var(--text-secondary)';
    }
  };

  const getPriorityBadgeClass = (priority) => {
    switch (priority) {
      case 'CRITICAL':
        return 'badge-peak';
      case 'HIGH':
        return 'badge-standard';
      case 'LOW':
        return 'badge-blue';
      default:
        return 'badge-standard';
    }
  };

  return (
    <div className="glass-card" style={{ padding: '1.25rem', height: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h2 style={{ fontSize: '1rem', fontWeight: '600' }}>Monitored Smart Appliances</h2>
        <span className="badge badge-blue">Fleet: {Object.keys(appliances).length}</span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        {Object.entries(appliances).map(([id, app]) => {
          const isRunning = app.status === 'ON' || app.status === 'ECO';

          return (
            <div
              key={id}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '0.75rem 1rem',
                backgroundColor: 'rgba(255, 255, 255, 0.03)',
                borderRadius: '8px',
                border: '1px solid var(--border-subtle)'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <div style={{
                  padding: '0.5rem',
                  borderRadius: '6px',
                  backgroundColor: 'rgba(255, 255, 255, 0.05)'
                }}>
                  {getIcon(app.category)}
                </div>
                <div>
                  <div style={{ fontSize: '0.875rem', fontWeight: '600' }}>{app.name}</div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.2rem' }}>
                    <span className={`badge ${getPriorityBadgeClass(app.priority)}`} style={{ fontSize: '0.65rem' }}>
                      {app.priority}
                    </span>
                    {app.setpoint_c && (
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                        Setpoint: {app.setpoint_c}°C
                      </span>
                    )}
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: '0.875rem', fontWeight: '700', color: getStatusColor(app.status) }}>
                    {app.status}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                    {app.power_kw?.toFixed(2)} kW
                  </div>
                </div>

                <button
                  className="btn-secondary"
                  title="Manual Toggle"
                  style={{ padding: '0.4rem 0.6rem' }}
                  onClick={() => {
                    if (onOverride) {
                      const nextStatus = isRunning ? 'OFF' : 'ON';
                      const power = nextStatus === 'ON' ? app.rated_power_kw : 0.0;
                      onOverride(id, { status: nextStatus, power_kw: power });
                    }
                  }}
                >
                  <Power size={14} color={isRunning ? 'var(--accent-emerald)' : 'var(--text-secondary)'} />
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
