import React from 'react';
import { Activity, Play, Zap, ShieldCheck } from 'lucide-react';

export function Header({ isConnected, simulationTime, onStepTrigger, isStepping }) {
  const formattedTime = simulationTime
    ? new Date(simulationTime).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : '--:--';

  return (
    <header className="glass-card" style={{ padding: '1rem 1.5rem', marginBottom: '1.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{
            background: 'linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%)',
            padding: '0.6rem',
            borderRadius: '10px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <Zap size={24} color="#ffffff" />
          </div>
          <div>
            <h1 style={{ fontSize: '1.25rem', fontWeight: '700', letterSpacing: '-0.025em' }}>
              Autonomous Smart Home AI Agent
            </h1>
            <p style={{ fontSize: '0.825rem', color: 'var(--text-secondary)' }}>
              Energy Optimization & Comfort Management Engine
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
          {/* Connection status */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem' }}>
            <span style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: isConnected ? 'var(--accent-emerald)' : 'var(--accent-rose)',
              boxShadow: isConnected ? '0 0 8px var(--accent-emerald)' : 'none'
            }} />
            <span style={{ color: 'var(--text-secondary)' }}>
              {isConnected ? 'Live WebSocket' : 'Disconnected'}
            </span>
          </div>

          {/* Clock badge */}
          <div className="badge badge-blue" style={{ fontSize: '0.85rem', padding: '0.35rem 0.75rem' }}>
            Sim Time: {formattedTime}
          </div>

          {/* Step Button */}
          <button
            className="btn-primary"
            onClick={onStepTrigger}
            disabled={isStepping}
            style={{ opacity: isStepping ? 0.7 : 1 }}
          >
            <Play size={16} />
            {isStepping ? 'Reasoning...' : 'Trigger Agent Step'}
          </button>
        </div>
      </div>
    </header>
  );
}
