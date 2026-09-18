/**
 * REST API client for backend communication.
 */

const BASE_URL = '/api';

export const api = {
  async getStatus() {
    const res = await fetch(`${BASE_URL}/status`);
    if (!res.ok) throw new Error('Failed to fetch system status');
    return res.json();
  },

  async getAppliances() {
    const res = await fetch(`${BASE_URL}/appliances`);
    if (!res.ok) throw new Error('Failed to fetch appliances');
    return res.json();
  },

  async overrideAppliance(applianceId, data) {
    const res = await fetch(`${BASE_URL}/appliances/${applianceId}/override`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error('Failed to override appliance');
    return res.json();
  },

  async triggerAgentStep() {
    const res = await fetch(`${BASE_URL}/agent/step`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!res.ok) throw new Error('Failed to execute agent step');
    return res.json();
  },

  async getHistory(limit = 50) {
    const res = await fetch(`${BASE_URL}/history?limit=${limit}`);
    if (!res.ok) throw new Error('Failed to fetch telemetry history');
    return res.json();
  },
};
