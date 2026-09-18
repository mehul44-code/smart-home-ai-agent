import React, { useState, useEffect } from 'react';
import { Header } from '../components/Header';
import { MetricsSummary } from '../components/MetricsSummary';
import { ApplianceCard } from '../components/ApplianceCard';
import { AgentReasoningBox } from '../components/AgentReasoningBox';
import { EnergyChart } from '../charts/EnergyChart';
import { TemperatureChart } from '../charts/TemperatureChart';
import { api } from '../services/api';
import { simulationSocket } from '../services/websocket';

export function DashboardPage() {
  const [isConnected, setIsConnected] = useState(false);
  const [currentState, setCurrentState] = useState(null);
  const [lastStepData, setLastStepData] = useState(null);
  const [historyData, setHistoryData] = useState([]);
  const [isStepping, setIsStepping] = useState(false);

  // Initialize data and WebSocket
  useEffect(() => {
    // 1. Initial REST fetch
    api.getStatus()
      .then((status) => {
        setCurrentState((prev) => ({ ...prev, ...status }));
      })
      .catch((err) => console.warn('Backend not yet reachable on mount:', err));

    api.getAppliances()
      .then((data) => {
        setCurrentState((prev) => ({ ...prev, appliances: data.appliances }));
      })
      .catch((err) => console.warn('Failed to load appliances:', err));

    api.getHistory(30)
      .then((res) => {
        if (res.history) setHistoryData(res.history);
      })
      .catch(() => {});

    // 2. Connect WebSocket
    simulationSocket.connect();

    const unsubConn = simulationSocket.on('connection_change', (status) => {
      setIsConnected(status);
    });

    const unsubConnected = simulationSocket.on('connected', (msg) => {
      if (msg.state) setCurrentState(msg.state);
    });

    const unsubTelemetry = simulationSocket.on('telemetry_update', (msg) => {
      if (msg.state) {
        setCurrentState(msg.state);
        setHistoryData((prev) => {
          const updated = [...prev, {
            timestamp: msg.state.timestamp,
            indoor_temp_c: msg.state.indoor_temp_c,
            outdoor_temp_c: msg.state.outdoor_temp_c,
            total_power_kw: msg.state.total_power_kw,
            solar_power_kw: msg.state.solar_generation_kw
          }];
          return updated.slice(-30);
        });
      }
    });

    const unsubStep = simulationSocket.on('agent_step', (msg) => {
      if (msg.data) {
        setLastStepData(msg.data);
        if (msg.data.consequent_state) {
          setCurrentState(msg.data.consequent_state);
        }
      }
    });

    return () => {
      unsubConn();
      unsubConnected();
      unsubTelemetry();
      unsubStep();
      simulationSocket.disconnect();
    };
  }, []);

  const handleStepTrigger = async () => {
    setIsStepping(true);
    try {
      const stepResult = await api.triggerAgentStep();
      setLastStepData(stepResult);
      if (stepResult.consequent_state) {
        setCurrentState(stepResult.consequent_state);
        setHistoryData((prev) => [
          ...prev.slice(-29),
          {
            timestamp: stepResult.consequent_state.timestamp,
            indoor_temp_c: stepResult.consequent_state.indoor_temp_c,
            outdoor_temp_c: stepResult.consequent_state.outdoor_temp_c,
            total_power_kw: stepResult.consequent_state.total_power_kw,
            solar_power_kw: stepResult.consequent_state.solar_generation_kw
          }
        ]);
      }
    } catch (err) {
      console.error('Failed to trigger step via REST:', err);
    } finally {
      setIsStepping(false);
    }
  };

  const handleApplianceOverride = async (applianceId, data) => {
    try {
      const res = await api.overrideAppliance(applianceId, data);
      if (res.current_state) {
        setCurrentState((prev) => ({
          ...prev,
          appliances: {
            ...prev.appliances,
            [applianceId]: res.current_state
          }
        }));
      }
    } catch (err) {
      console.error('Failed to override appliance:', err);
    }
  };

  return (
    <div style={{ maxWidth: '1440px', margin: '0 auto', padding: '1.5rem' }}>
      <Header
        isConnected={isConnected}
        simulationTime={currentState?.timestamp}
        onStepTrigger={handleStepTrigger}
        isStepping={isStepping}
      />

      <MetricsSummary state={currentState} />

      {/* 7-Stage Cognitive Decision Agent Centerpiece */}
      <AgentReasoningBox lastStepData={lastStepData} />

      {/* Split grid: Left = Appliances, Right = Charts */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))',
        gap: '1.5rem',
        alignItems: 'start'
      }}>
        <ApplianceCard
          appliances={currentState?.appliances}
          onOverride={handleApplianceOverride}
        />

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <TemperatureChart
            data={historyData}
            targetTemp={currentState?.target_temp_c ?? 22.0}
          />
          <EnergyChart
            data={historyData}
          />
        </div>
      </div>
    </div>
  );
}
