const configuredUrl = import.meta.env.VITE_BACKEND_URL || '';

function socketUrl() {
  if (configuredUrl) {
    const url = new URL(configuredUrl);
    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${url.toString().replace(/\/$/, '')}/ws/home`;
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}/ws/home`;
}

class HomeWebSocket {
  constructor() { this.listeners = new Map(); this.retry = 0; this.closed = false; }
  on(event, callback) {
    if (!this.listeners.has(event)) this.listeners.set(event, new Set());
    this.listeners.get(event).add(callback);
    return () => this.listeners.get(event)?.delete(callback);
  }
  emit(event, data) { this.listeners.get(event)?.forEach((callback) => callback(data)); }
  connect() {
    this.closed = false;
    this.emit('status', 'reconnecting');
    try {
      this.ws = new WebSocket(socketUrl());
      this.ws.onopen = () => { this.retry = 0; this.emit('status', 'connected'); };
      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          this.emit(message.event || 'message', message);
        } catch { this.emit('error', { detail: 'Invalid WebSocket message' }); }
      };
      this.ws.onerror = () => this.emit('error', { detail: 'WebSocket connection error' });
      this.ws.onclose = () => {
        this.emit('status', 'disconnected');
        if (!this.closed) {
          const delay = Math.min(1000 * 2 ** this.retry, 10000);
          this.retry += 1;
          this.timer = setTimeout(() => this.connect(), delay);
        }
      };
    } catch (error) { this.emit('error', error); }
  }
  disconnect() {
    this.closed = true;
    clearTimeout(this.timer);
    this.ws?.close();
  }
}

export const homeSocket = new HomeWebSocket();
export const simulationSocket = homeSocket;
