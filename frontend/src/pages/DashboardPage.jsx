import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Activity, AlertTriangle, BrainCircuit, Check, ChevronRight, Cpu, Gauge, Home, Lightbulb,
  Loader2, Play, Power, RefreshCw, Settings2, Sparkles, Thermometer, Users, Zap,
} from 'lucide-react';
import {
  Area, AreaChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { api } from '../services/api';
import { homeSocket } from '../services/websocket';

const scenarios = [
  ['NORMAL_HOME', 'Normal home'], ['HOT_OCCUPIED_ROOM', 'Hot room'], ['EMPTY_ROOM', 'Empty room'],
  ['PEAK_TARIFF', 'Peak tariff'], ['HIGH_ENERGY_LOAD', 'High energy load'], ['ENERGY_ANOMALY', 'Energy anomaly'],
  ['USER_OVERRIDE', 'User override'], ['PEAK_TARIFF_LAUNDRY', 'Peak tariff laundry'],
  ['OFF_PEAK_LAUNDRY', 'Off-peak laundry'], ['HIGH_PRIORITY_LAUNDRY', 'High-priority laundry'],
  ['HIGH_LOAD_WATER_HEATER', 'High-load water heater'],
];
const stages = ['PERCEPTION', 'PREDICTION', 'REASONING', 'DECISION', 'ACTION', 'FEEDBACK'];
const readable = (value, fallback = '—') => value === null || value === undefined ? fallback : value;
const kw = (watts) => `${(Number(watts || 0) / 1000).toFixed(2)} kW`;
const time = (value) => value ? new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—';
const tariffName = (tariff) => String(tariff?.tier || tariff?.period || 'NORMAL').replaceAll('_', ' ');

function Metric({ icon: Icon, label, value, detail, accent = 'blue' }) {
  return <div className="metric-card"><div className={`metric-icon ${accent}`}><Icon size={18} /></div><div><div className="eyebrow">{label}</div><strong>{value}</strong>{detail && <small>{detail}</small>}</div></div>;
}
function Card({ title, eyebrow, icon: Icon, children, className = '' }) {
  return <section className={`card ${className}`}><div className="card-heading">{Icon && <Icon size={18} className="heading-icon" />}<div>{eyebrow && <span className="eyebrow">{eyebrow}</span>}<h2>{title}</h2></div></div>{children}</section>;
}
function Empty({ text = 'No data available yet.' }) { return <div className="empty"><Activity size={18} />{text}</div>; }

export function DashboardPage() {
  const [state, setState] = useState(null);
  const [status, setStatus] = useState(null);
  const [energy, setEnergy] = useState(null);
  const [tariff, setTariff] = useState(null);
  const [preferences, setPreferences] = useState(null);
  const [agent, setAgent] = useState(null);
  const [anomalies, setAnomalies] = useState([]);
  const [history, setHistory] = useState([]);
  const [wsStatus, setWsStatus] = useState('disconnected');
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [lastStep, setLastStep] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const [nextState, nextStatus, nextEnergy, nextTariff, nextPrefs, nextAgent, nextAnomalies, nextHistory] = await Promise.all([
        api.getState(), api.getStatus(), api.getEnergy(50), api.getTariff(50), api.getPreferences(),
        api.getAgentStatus(), api.getAnomalies(20), api.getAgentHistory(20),
      ]);
      setState(nextState); setStatus(nextStatus); setEnergy(nextEnergy); setTariff(nextTariff);
      setPreferences(nextPrefs); setAgent(nextAgent); setAnomalies(nextAnomalies.anomalies || []);
      setHistory(nextHistory.history || []);
      setError('');
    } catch (err) { setError(err.message || 'Backend unavailable. Start the API to connect.'); }
  }, []);

  useEffect(() => {
    refresh();
    const unsubStatus = homeSocket.on('status', setWsStatus);
    const unsubConnected = homeSocket.on('connected', (message) => setState(message.state));
    const unsubState = homeSocket.on('state_update', (message) => {
      setState(message.state);
      setStatus((previous) => previous ? { ...previous, simulation_time: message.state?.timestamp } : previous);
    });
    const unsubError = homeSocket.on('error', (message) => setError(message.detail || 'WebSocket error'));
    homeSocket.connect();
    return () => { unsubStatus(); unsubConnected(); unsubState(); unsubError(); homeSocket.disconnect(); };
  }, [refresh]);

  const run = async (key, operation) => {
    setBusy(key); setError('');
    try {
      const result = await operation();
      if (result?.stage_1_perception) {
        setLastStep(result);
        if (result.snapshot) {
          setState(result.snapshot);
          setStatus((previous) => previous ? { ...previous, simulation_time: result.snapshot.timestamp || previous.simulation_time } : previous);
        }
      }
      await refresh();
    } catch (err) { setError(err.message || 'Action failed'); }
    finally { setBusy(''); }
  };
  const step = () => run('step', async () => { const result = await api.triggerAgentStep(); setLastStep(result); return result; });
  const applianceAction = (id, app, mode) => run(id, () => api.applianceAction(id, {
    // The simulator accepts SET_MODE as its non-override control path; AUTO
    // uses its ECO operating mode while leaving the user override flag false.
    action: mode === 'AUTO' ? 'SET_MODE' : mode, status: mode === 'AUTO' ? 'ECO' : mode,
    power_watts: mode === 'ON' ? app.nominal_power_watts : 0, is_user_override: mode !== 'AUTO',
  }));
  const selectMode = (mode) => run('preference', () => api.savePreferences({
    preferred_temperature: preferences?.preferred_temperature ?? 22, comfort_priority: mode === 'COMFORT' ? 0.8 : 0.5,
    energy_priority: mode === 'ENERGY_SAVING' ? 0.8 : 0.5, selected_mode: mode, manual_override: false,
  }));

  const cycleState = lastStep?.snapshot || state || {};
  const rooms = cycleState?.rooms || state?.rooms || {};
  const appliances = cycleState?.appliances || state?.appliances || {};
  const currentTariff = cycleState?.tariff || tariff?.current || state?.tariff || {};
  const chartData = useMemo(() => (energy?.history || []).slice().reverse().map((item) => ({
    time: time(item.timestamp), energy: Number(item.energy_kwh || item.total_energy_kwh || 0),
    load: Number(item.total_load_watts || 0) / 1000,
  })), [energy]);
  const decision = lastStep?.stage_4_decision;
  const prediction = lastStep?.stage_2_prediction || {};
  const feedback = lastStep?.stage_6_feedback || {};
  const candidates = lastStep?.stage_3_reasoning?.candidates_evaluated || [];

  return <div className="dashboard">
    <header className="topbar">
      <div className="brand"><div className="brand-mark"><Zap size={22} /></div><div><h1>Autonomous AI Smart Home Agent</h1><p>Energy Optimization <span>+</span> Comfort Management</p></div></div>
      <div className="top-actions"><span className={`connection ${wsStatus}`}><i /> {wsStatus === 'connected' ? 'Live' : wsStatus}</span><span className="sim-clock">{time(state?.timestamp || status?.simulation_time)}</span><button className="primary" onClick={step} disabled={busy === 'step'}>{busy === 'step' ? <Loader2 className="spin" size={16} /> : <Play size={16} />} Run agent step</button></div>
    </header>
    {error && <div className="error-banner"><AlertTriangle size={17} />{error}<button onClick={() => { setError(''); refresh(); }}><RefreshCw size={15} /></button></div>}

    <div className="metric-grid">
      <Metric icon={Thermometer} label="Indoor temperature" value={`${readable(rooms.living_room?.temperature_c)}°C`} detail={`Humidity ${readable(rooms.living_room?.humidity_pct)}%`} accent="orange" />
      <Metric icon={Users} label="Occupancy" value={cycleState?.occupancy?.total_occupants ?? cycleState?.occupancy_detail?.total_occupants ?? 0} detail={(cycleState?.occupancy?.is_occupied ?? cycleState?.occupancy_detail?.is_occupied) ? 'People detected' : 'No one home'} accent="purple" />
      <Metric icon={Gauge} label="Current load" value={kw(cycleState?.total_load_watts)} detail={`Energy ${readable(cycleState?.total_energy_kwh, '—')} kWh`} accent="blue" />
      <Metric icon={Zap} label="Electricity tariff" value={tariffName(currentTariff)} detail={currentTariff.rate != null ? `₹${Number(currentTariff.rate).toFixed(2)}/kWh now · next off-peak ₹${Number(currentTariff.next_off_peak_rate ?? currentTariff.next_rate ?? currentTariff.rate).toFixed(2)}/kWh in ${currentTariff.next_off_peak_minutes ?? currentTariff.minutes_until_next_tier ?? 0} min` : 'Rate unavailable'} accent="green" />
      <Metric icon={Sparkles} label="Comfort score" value={feedback.comfort_satisfaction_pct != null ? `${feedback.comfort_satisfaction_pct}%` : '—'} detail="Latest agent feedback" accent="teal" />
      <Metric icon={Activity} label="Energy saved" value={lastStep?.stage_4_decision?.estimated_energy_saving_kwh != null ? `${lastStep.stage_4_decision.estimated_energy_saving_kwh} kWh` : '—'} detail="Backend comparison" accent="green" />
    </div>

    <div className="hero-grid">
      <Card title="Agent decision" eyebrow="Autonomous control loop" icon={BrainCircuit} className="decision-card">
        <div className="decision-main">{decision ? <><div className="decision-action">{String(decision.chosen_strategy || decision.selected_action || 'Decision ready').replaceAll('_', ' ')}</div><div className="decision-reason">{lastStep.stage_7_explanation || 'The agent selected an action from its evaluated candidates.'}</div></> : <Empty text="Run an agent step to see perception → prediction → reasoning → action." />}</div>
        <div className="pipeline">{stages.map((stage, index) => <React.Fragment key={stage}><div className={`pipeline-stage ${lastStep && index <= 5 ? 'done' : ''}`}><span>{lastStep && index < 5 ? <Check size={12} /> : index + 1}</span>{stage}</div>{index < stages.length - 1 && <ChevronRight size={14} />}</React.Fragment>)}</div>
        {lastStep && <div className="decision-grid"><div><span>Cooling requirement</span><b>{readable(prediction.cooling_energy_needed_kwh)} kWh</b></div><div><span>Prediction source</span><b>{readable(prediction.prediction_source)}</b></div><div><span>Expected energy</span><b>{readable(decision.expected_energy_kwh)} kWh</b></div><div><span>Expected cost</span><b>{readable(decision.projected_hourly_cost_usd)}</b></div></div>}
      </Card>
      <Card title="Appliance recommendations" eyebrow="Washing machine · water heater" icon={Power} className="explain-card">
        {lastStep?.appliance_decisions ? Object.entries(lastStep.appliance_decisions).map(([id, item]) => <div className="mini-list" key={id}>
          <div><span>{id.replaceAll('_', ' ')}</span><b>{item.selected_action || item.chosen_strategy}</b></div>
          <small>{item.reason}</small>
          <small>Load: household {readable(item.household_load_kw)} kW · appliance {readable(item.appliance_load_kw)} kW{item.projected_load_kw != null ? ` · projected ${item.projected_load_kw} kW` : ''}</small>
          {id === 'washing_machine' && <small>Tariff: ₹{Number(item.current_tariff_rate || 0).toFixed(2)}/kWh now → ₹{Number(item.future_tariff_rate || 0).toFixed(2)}/kWh later · cost ₹{Number(item.current_cost || 0).toFixed(2)} → ₹{Number(item.delayed_cost || 0).toFixed(2)} · saving ₹{Number(item.savings || 0).toFixed(2)}</small>}
          {id === 'water_heater' && <small>Peak load: +{readable(item.heater_addition_kw)} kW heater → {readable(item.peak_load_after_kw)} kW ({readable(item.peak_status)}); AC {readable(item.ac_interaction)}, washer {readable(item.washing_machine_interaction)}</small>}
          {item.schedule && <small>Schedule: {item.schedule.status} in {item.schedule.delay_minutes} min at ₹{Number(item.schedule.target_rate || 0).toFixed(2)}/kWh · start {time(item.planned_start)}</small>}
          <small>Priority: {readable(item.priority)} · {item.override_respected ? 'Override respected' : 'Autonomous control'}</small>
        </div>) : <Empty text="Run an agent step to see appliance recommendations." />}
      </Card>
      <Card title="Why this decision?" eyebrow="Explainable reasoning" icon={Sparkles} className="explain-card">
        {lastStep ? <><p className="explanation">{lastStep.stage_7_explanation}</p><div className="mini-list"><div><span>Observed temperature</span><b>{readable(lastStep.stage_1_perception?.indoor_temperature_c)}°C</b></div><div><span>Occupancy</span><b>{readable(lastStep.stage_1_perception?.occupancy)}</b></div><div><span>Tariff</span><b>{readable(lastStep.stage_1_perception?.tariff_tier)}</b></div><div><span>Feedback</span><b>{readable(feedback.feedback_signal)}</b></div></div></> : <Empty text="The agent's natural-language rationale appears here." />}
      </Card>
    </div>

    <div className="content-grid">
      <Card title="Rooms" eyebrow="Perception layer" icon={Home}><div className="room-grid">{Object.entries(rooms).map(([id, room]) => <div className="room" key={id}><div className="room-title"><Home size={15} />{String(room.name || id).replaceAll('_', ' ')}</div><div className="room-reading"><strong>{readable(room.temperature_c)}°</strong><span>{readable(room.humidity_pct)}% RH</span><span>{room.occupancy_count ?? 0} people</span></div><small>{Object.values(appliances).filter((app) => app.room === id).map((app) => app.name).join(' · ') || 'No appliances reported'}</small></div>)}</div></Card>
      <Card title="AI predictions" eyebrow="Prediction layer" icon={Cpu}><div className="prediction-grid">{[['Energy', prediction.energy_prediction], ['Occupancy', prediction.occupancy_prediction], ['Cooling', prediction.cooling_requirement || prediction.cooling_energy_needed_kwh], ['Comfort', prediction.comfort_prediction], ['Anomaly', prediction.energy_anomaly]].map(([label, value]) => <div className="prediction" key={label}><span>{label}</span><b>{readable(value)}</b><small>{readable(prediction.prediction_source, 'Backend model')}</small></div>)}</div></Card>
    </div>

    <div className="content-grid">
      <Card title="Appliance control" eyebrow={`${Object.keys(appliances).length} connected devices`} icon={Power} className="appliance-card"><div className="appliance-list">{Object.entries(appliances).map(([id, app]) => <div className="appliance" key={id}><div className="appliance-icon"><Lightbulb size={17} /></div><div className="appliance-info"><b>{app.name || id}</b><small>{String(app.room || 'home').replaceAll('_', ' ')} · {app.priority || 'STANDARD'}</small></div><div className="appliance-reading"><b>{app.status || '—'}</b><small>{kw(app.power_watts)}</small></div><div className="mode-buttons">{['AUTO', 'ON', 'OFF'].map((mode) => <button key={mode} className={(app.status === mode || (mode === 'AUTO' && !app.is_user_override)) ? 'selected' : ''} onClick={() => applianceAction(id, app, mode)} disabled={busy === id}>{mode}</button>)}</div></div>)}</div></Card>
      <Card title="Candidate actions" eyebrow="Multi-objective reasoning" icon={Settings2}>{candidates.length ? <div className="candidate-list">{candidates.map((candidate) => <div className={`candidate ${candidate.id === decision?.chosen_strategy ? 'chosen' : ''}`} key={candidate.id}><span>{candidate.label || candidate.id}</span><b>{readable(candidate.total_utility ?? candidate.total_loss)}</b><small>utility score</small></div>)}</div> : <Empty text="Candidate utilities are shown after an agent step." />}</Card>
    </div>

    <div className="content-grid">
      <Card title="Energy analytics" eyebrow="Historical backend records" icon={Activity} className="chart-card">{chartData.length ? <ResponsiveContainer width="100%" height={220}><AreaChart data={chartData}><defs><linearGradient id="loadFill" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#1d73e8" stopOpacity={0.25} /><stop offset="95%" stopColor="#1d73e8" stopOpacity={0} /></linearGradient></defs><CartesianGrid stroke="#e5edf5" vertical={false} /><XAxis dataKey="time" tick={{ fontSize: 11 }} /><YAxis tick={{ fontSize: 11 }} /><Tooltip /><Area type="monotone" dataKey="load" name="Load (kW)" stroke="#1d73e8" fill="url(#loadFill)" /><Line type="monotone" dataKey="energy" name="Energy (kWh)" stroke="#16a38a" /></AreaChart></ResponsiveContainer> : <Empty text="Historical energy data will appear as the simulator records readings." />}</Card>
      <Card title="Latest feedback" eyebrow="Closed-loop validation" icon={RefreshCw}>{lastStep ? <div className="feedback"><div><span>Actual temperature</span><b>{readable(feedback.actual_indoor_temp_c)}°C</b></div><div><span>Comfort result</span><b>{readable(feedback.comfort_satisfaction_pct)}%</b></div><div><span>Decision</span><b>{readable(feedback.feedback_signal)}</b></div></div> : <Empty text="No feedback recorded yet." />}</Card>
    </div>

    <div className="content-grid">
      <Card title="Alerts & anomalies" eyebrow="Safety monitoring" icon={AlertTriangle}>{anomalies.length ? <div className="anomaly-list">{anomalies.slice(0, 5).map((item) => <div className="anomaly" key={item.id}><AlertTriangle size={17} /><div><b>{item.appliance || 'Home energy'}</b><small>Expected {item.expected_power} W · actual {item.actual_power} W · deviation {item.deviation} W</small></div><span>{item.severity}</span></div>)}</div> : <Empty text="No anomaly records reported by the backend." />}</Card>
      <Card title="User preference mode" eyebrow="Agent objective weights" icon={Users}><div className="preference-buttons">{['BALANCED', 'COMFORT', 'ENERGY_SAVING'].map((mode) => <button key={mode} className={preferences?.selected_mode === mode ? 'selected' : ''} onClick={() => selectMode(mode)} disabled={busy === 'preference'}>{mode.replace('_', ' ')}</button>)}</div><p className="muted">Saved mode: <b>{preferences?.selected_mode || '—'}</b>. Changes are persisted through the agent API.</p></Card>
    </div>

    <Card title="Competition demo" eyebrow="Backend scenarios" icon={Play}><div className="scenario-list">{scenarios.map(([id, label]) => <button key={id} onClick={() => run(id, async () => { await api.loadScenario(id); return api.triggerAgentStep(); })} disabled={busy === id}>{busy === id ? <Loader2 className="spin" size={14} /> : <Play size={14} />}{label}</button>)}</div></Card>
  </div>;
}
