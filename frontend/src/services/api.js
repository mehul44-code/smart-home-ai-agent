const configuredUrl = import.meta.env.VITE_BACKEND_URL || '';
const API_ROOT = `${configuredUrl.replace(/\/$/, '')}/api`;

async function request(path, options = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10000);
  try {
    const response = await fetch(`${API_ROOT}${path}`, {
      ...options,
      signal: controller.signal,
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.detail || `Request failed (${response.status})`);
    return body;
  } finally {
    clearTimeout(timeout);
  }
}

export const api = {
  getState: () => request('/simulation/state'),
  getStatus: () => request('/status'),
  getAppliances: () => request('/appliances'),
  getEnergy: (limit = 50) => request(`/energy?limit=${limit}`),
  getTariff: (limit = 50) => request(`/tariff?limit=${limit}`),
  getPreferences: () => request('/preferences'),
  getAgentStatus: () => request('/agent/status'),
  getAgentHistory: (limit = 20) => request(`/agent/history?limit=${limit}`),
  getAnomalies: (limit = 20) => request(`/anomalies?limit=${limit}`),
  triggerAgentStep: () => request('/agent/step', { method: 'POST' }),
  applianceAction: (id, action) => request(`/appliances/${encodeURIComponent(id)}/action`, {
    method: 'POST', body: JSON.stringify(action),
  }),
  overrideAppliance: (id, action) => request(`/override?appliance_id=${encodeURIComponent(id)}`, {
    method: 'POST', body: JSON.stringify({ ...action, is_user_override: true, source: 'USER' }),
  }),
  savePreferences: (preferences) => request('/preferences', {
    method: 'POST', body: JSON.stringify(preferences),
  }),
  loadScenario: (scenario_id) => request('/simulation/scenario', {
    method: 'POST', body: JSON.stringify({ scenario_id }),
  }),
};
