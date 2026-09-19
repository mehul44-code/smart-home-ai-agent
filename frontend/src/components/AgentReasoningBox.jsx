import React, { useState } from 'react';
import { Eye, TrendingUp, Cpu, CheckCircle2, PlayCircle, RefreshCw, MessageSquare, ChevronDown, ChevronRight } from 'lucide-react';

export function AgentReasoningBox({ lastStepData }) {
  const [activeStageTab, setActiveStageTab] = useState('explanation');

  if (!lastStepData) {
    return (
      <div className="glass-card" style={{ padding: '1.5rem', textAlign: 'center' }}>
        <p style={{ color: 'var(--text-secondary)' }}>
          Agent is standing by. Click <strong>"Trigger Agent Step"</strong> above to observe the 7-stage cognitive loop.
        </p>
      </div>
    );
  }

  const stages = [
    { key: 'perception', label: '1. Perception', icon: <Eye size={16} />, data: lastStepData.stage_1_perception },
    { key: 'prediction', label: '2. Prediction', icon: <TrendingUp size={16} />, data: lastStepData.stage_2_prediction },
    { key: 'reasoning', label: '3. Reasoning', icon: <Cpu size={16} />, data: lastStepData.stage_3_reasoning },
    { key: 'decision', label: '4. Decision', icon: <CheckCircle2 size={16} />, data: lastStepData.stage_4_decision },
    { key: 'action', label: '5. Action', icon: <PlayCircle size={16} />, data: lastStepData.stage_5_action },
    { key: 'feedback', label: '6. Feedback', icon: <RefreshCw size={16} />, data: lastStepData.stage_6_feedback },
    { key: 'explanation', label: '7. Explanation', icon: <MessageSquare size={16} />, data: lastStepData.stage_7_explanation }
  ];

  return (
    <div className="glass-card" style={{ padding: '1.5rem', marginBottom: '1.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <div>
          <h2 style={{ fontSize: '1.1rem', fontWeight: '700', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Cpu size={20} color="var(--accent-blue)" />
            Autonomous 7-Stage Cognitive Decision Pipeline
          </h2>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            Step #{lastStepData.step_id} executed at {lastStepData.timestamp}
          </span>
        </div>
        <span className="badge badge-peak" style={{ backgroundColor: 'rgba(59, 130, 246, 0.15)', color: 'var(--accent-blue)' }}>
          Strategy: {lastStepData.stage_4_decision?.chosen_strategy}
        </span>
      </div>

      {/* Stage Selector Pills */}
      <div style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: '0.5rem',
        marginBottom: '1rem',
        paddingBottom: '0.75rem',
        borderBottom: '1px solid var(--border-subtle)'
      }}>
        {stages.map((stage) => {
          const isActive = activeStageTab === stage.key;
          return (
            <button
              key={stage.key}
              onClick={() => setActiveStageTab(stage.key)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.4rem',
                padding: '0.4rem 0.8rem',
                borderRadius: '6px',
                fontSize: '0.8rem',
                fontWeight: isActive ? '600' : '500',
                backgroundColor: isActive ? 'var(--accent-blue)' : 'rgba(255, 255, 255, 0.05)',
                color: isActive ? '#ffffff' : 'var(--text-secondary)',
                border: '1px solid',
                borderColor: isActive ? 'var(--accent-blue)' : 'transparent',
                cursor: 'pointer',
                transition: 'all 0.15s'
              }}
            >
              {stage.icon}
              {stage.label}
            </button>
          );
        })}
      </div>

      {/* Stage Content Renderers */}
      <div style={{
        backgroundColor: 'rgba(0, 0, 0, 0.25)',
        borderRadius: '8px',
        padding: '1.25rem',
        border: '1px solid var(--border-subtle)',
        minHeight: '140px'
      }}>
        {activeStageTab === 'explanation' && (
          <div>
            <h3 style={{ fontSize: '0.9rem', color: 'var(--accent-cyan)', marginBottom: '0.5rem' }}>
              Natural Language Rationale & Trade-off Synthesis:
            </h3>
            <p style={{ fontSize: '0.95rem', lineHeight: '1.6', color: 'var(--text-primary)' }}>
              {lastStepData.stage_7_explanation}
            </p>
          </div>
        )}

        {activeStageTab === 'perception' && (
          <pre style={{ fontSize: '0.8rem', color: '#e2e8f0', overflowX: 'auto' }}>
            {JSON.stringify(lastStepData.stage_1_perception, null, 2)}
          </pre>
        )}

        {activeStageTab === 'prediction' && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
            <div>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Projected Temp Drift (Off)</span>
              <div style={{ fontSize: '1.25rem', fontWeight: '700', color: 'var(--accent-amber)' }}>
                +{lastStepData.stage_2_prediction?.projected_temp_drift_c}°C
              </div>
            </div>
            <div>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Estimated Energy Needed</span>
              <div style={{ fontSize: '1.25rem', fontWeight: '700', color: 'var(--accent-cyan)' }}>
                {lastStepData.stage_2_prediction?.cooling_energy_needed_kwh} kWh
              </div>
            </div>
            <div>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Comfort Risk Index</span>
              <div style={{ fontSize: '1.25rem', fontWeight: '700', color: 'var(--accent-rose)' }}>
                {lastStepData.stage_2_prediction?.comfort_risk}
              </div>
            </div>
          </div>
        )}

        {activeStageTab === 'reasoning' && (
          <div>
            <h4 style={{ fontSize: '0.85rem', marginBottom: '0.75rem', color: 'var(--text-secondary)' }}>
              Multi-Objective Candidate Evaluations (Lower Loss is Optimal):
            </h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {lastStepData.stage_3_reasoning?.candidates_evaluated?.map((cand) => (
                <div
                  key={cand.id}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    padding: '0.5rem 0.75rem',
                    borderRadius: '6px',
                    backgroundColor: cand.id === lastStepData.stage_3_reasoning.preferred_candidate ? 'rgba(59, 130, 246, 0.15)' : 'rgba(255, 255, 255, 0.02)',
                    border: cand.id === lastStepData.stage_3_reasoning.preferred_candidate ? '1px solid var(--accent-blue)' : '1px solid transparent',
                    fontSize: '0.8rem'
                  }}
                >
                  <span style={{ fontWeight: '600' }}>{cand.label}</span>
                  <div style={{ display: 'flex', gap: '1rem', color: 'var(--text-secondary)' }}>
                    <span>Comfort Loss: {cand.comfort_penalty}</span>
                    <span>Cost Loss: {cand.cost_penalty}</span>
                    <strong style={{ color: cand.id === lastStepData.stage_3_reasoning.preferred_candidate ? 'var(--accent-emerald)' : 'inherit' }}>
                      Total Loss: {cand.total_loss}
                    </strong>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeStageTab === 'decision' && (
          <pre style={{ fontSize: '0.8rem', color: '#e2e8f0', overflowX: 'auto' }}>
            {JSON.stringify(lastStepData.stage_4_decision, null, 2)}
          </pre>
        )}

        {activeStageTab === 'action' && (
          <pre style={{ fontSize: '0.8rem', color: '#e2e8f0', overflowX: 'auto' }}>
            {JSON.stringify(lastStepData.stage_5_action, null, 2)}
          </pre>
        )}

        {activeStageTab === 'feedback' && (
          <div style={{ display: 'flex', gap: '2rem', flexWrap: 'wrap' }}>
            <div>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Post-Action Indoor Temp</span>
              <div style={{ fontSize: '1.25rem', fontWeight: '700', color: 'var(--accent-cyan)' }}>
                {lastStepData.stage_6_feedback?.actual_indoor_temp_c}°C
              </div>
            </div>
            <div>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Satisfaction Score</span>
              <div style={{ fontSize: '1.25rem', fontWeight: '700', color: 'var(--accent-emerald)' }}>
                {lastStepData.stage_6_feedback?.comfort_satisfaction_pct}%
              </div>
            </div>
            <div>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Feedback Quality Signal</span>
              <div className="badge badge-off-peak" style={{ marginTop: '0.25rem' }}>
                {lastStepData.stage_6_feedback?.feedback_signal}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
