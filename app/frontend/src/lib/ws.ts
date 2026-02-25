import type { WsEvent } from '../types';

type Listener = (event: WsEvent) => void;

const wsBase = (import.meta.env.VITE_API_BASE_WS as string | undefined) ?? 'ws://localhost:8000';

export class StatusWebSocket {
  private socket: WebSocket | null = null;
  private listeners = new Set<Listener>();
  private reconnectAttempts = 0;
  private closedByUser = false;

  connect() {
    if (this.socket) return;
    this.closedByUser = false;
    const url = `${wsBase}/ws/status`;
    this.socket = new WebSocket(url);

    this.socket.onopen = () => {
      this.reconnectAttempts = 0;
    };

    this.socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as WsEvent;
        this.listeners.forEach((cb) => cb(data));
      } catch (error) {
        console.error('Failed to parse websocket payload', error);
      }
    };

    this.socket.onclose = () => {
      this.socket = null;
      if (!this.closedByUser) {
        this.scheduleReconnect();
      }
    };

    this.socket.onerror = () => {
      this.socket?.close();
    };
  }

  disconnect() {
    this.closedByUser = true;
    this.socket?.close();
    this.socket = null;
  }

  addListener(listener: Listener) {
    this.listeners.add(listener);
  }

  removeListener(listener: Listener) {
    this.listeners.delete(listener);
  }

  private scheduleReconnect() {
    this.reconnectAttempts += 1;
    const timeout = Math.min(1000 * 2 ** this.reconnectAttempts, 30_000);
    setTimeout(() => {
      if (!this.socket) {
        this.connect();
      }
    }, timeout);
  }
}

export const statusSocket = new StatusWebSocket();
