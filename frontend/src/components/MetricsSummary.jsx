import React from 'react';
import { Thermometer, Zap, DollarSign, Users, Sun } from 'lucide-react';

export function MetricsSummary({ state }) {
  if (!state) return null;

  const tariffTier = state.tariff?.tier || 'STANDARD';
  const tariffBadgeClass =
    tariffTier === 'PEAK' || tariffTier === 'CRITICAL_PEAK'
      ? 'badge-peak'
      : tariffTier === 'OFF_PEAK'
      ? 'badge-off-peak'
      : 'badge-standard';

  const cards = [
    {
      title: 'Indoor vs Target',
      value: `${state.indoor_temp_c ?? '--'}°C`,
      subtitle: `Target: ${state.target_temp_c ?? 22.0}°C | Outdoor: ${state.outdoor_temp_c ?? '--'}°C`,
      icon: <Thermometer size={20} color="var(--accent-cyan)" />,
      accentColor: 'var(--accent-cyan)'
    },
    {
      title: 'Grid Power Draw',
      value: `${state.grid_power_kw ?? '--'} kW`,
      subtitle: `Total Load: ${state.total_power_kw ?? '--'} kW`,
      icon: <Zap size={20} color="var(--accent-amber)" />,
      accentColor: 'var(--accent-amber)'
    },
    {
      title: 'Electricity Tariff',
      value: `$${state.tariff?.rate?.toFixed(2) ?? '0.16'}/kWh`,
      badge: tariffTier,
      badgeClass: tariffBadgeClass,
      icon: <DollarSign size={20} color="var(--accent-emerald)" />,
      accentColor: 'var(--accent-emerald)'
    },
    {
      title: 'Solar & Occupancy',
      value: `${state.solar_generation_kw ?? 0} kW PV`,
      subtitle: state.occupancy ? `Occupied (${state.occupant_count ?? 1} people)` : 'Unoccupied (Eco Mode)',
      icon: <Sun size={20} color="var(--accent-purple)" />,
      accentColor: 'var(--accent-purple)'
    }
  ];

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
      gap: '1rem',
      marginBottom: '1.5rem'
    }}>
      {cards.map((c, i) => (
        <div key={i} className="glass-card" style={{ padding: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
            <span style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', fontWeight: '500' }}>
              {c.title}
            </span>
            <div style={{
              padding: '0.4rem',
              borderRadius: '8px',
              backgroundColor: 'rgba(255, 255, 255, 0.05)'
            }}>
              {c.icon}
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.6rem' }}>
            <div style={{ fontSize: '1.65rem', fontWeight: '700', letterSpacing: '-0.02em' }}>
              {c.value}
            </div>
            {c.badge && (
              <span className={`badge ${c.badgeClass}`}>
                {c.badge}
              </span>
            )}
          </div>
          {c.subtitle && (
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.4rem' }}>
              {c.subtitle}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
