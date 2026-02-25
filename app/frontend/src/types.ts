export type AgentStatus = 'running' | 'idle' | 'stopped';

export interface AgentInfo {
  id: string;
  name: string;
  cpu: number;
  mem: number;
  status: AgentStatus;
}

export interface GatewayStatus {
  online: boolean;
  uptime_s: number;
}

export interface MetricPoint {
  t: number;
  cpu: number;
  mem: number;
  pnl: number;
}

export interface CommandRequest {
  text: string;
}

export interface CommandResponse {
  ok: boolean;
  message: string;
}

export interface StatusResponse {
  gateway: GatewayStatus;
  agents: AgentInfo[];
}

export interface WsLogEvent {
  type: 'log';
  line: string;
}

export interface WsAgentEvent {
  type: 'agent';
  id: string;
  status: AgentStatus;
  cpu: number;
  mem: number;
}

export interface WsGatewayEvent {
  type: 'gateway';
  online: boolean;
}

export type WsEvent = WsLogEvent | WsAgentEvent | WsGatewayEvent;
