import axios from 'axios';
import { z } from 'zod';
import type {
  AgentInfo,
  CommandResponse,
  GatewayStatus,
  MetricPoint,
  StatusResponse
} from '../types';

const apiBase = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000';

const agentSchema = z.object({
  id: z.string(),
  name: z.string(),
  cpu: z.number(),
  mem: z.number(),
  status: z.enum(['running', 'idle', 'stopped'])
});

const agentsSchema = z.array(agentSchema);

const gatewaySchema = z.object({
  online: z.boolean(),
  uptime_s: z.number()
});

const statusSchema = z.object({
  gateway: gatewaySchema,
  agents: agentsSchema
});

const metricsSchema = z.array(
  z.object({
    t: z.number(),
    cpu: z.number(),
    mem: z.number(),
    pnl: z.number()
  })
);

const commandResponseSchema = z.object({
  ok: z.boolean(),
  message: z.string()
});

async function parseResponse<T>(promise: Promise<{ data: unknown }>, schema: z.ZodType<T>): Promise<T> {
  const { data } = await promise;
  const parsed = schema.safeParse(data);
  if (!parsed.success) {
    console.error('API parse error', parsed.error.flatten());
    throw new Error('Unexpected API response');
  }
  return parsed.data;
}

export const getAgents = async (): Promise<AgentInfo[]> =>
  parseResponse(axios.get(`${apiBase}/agents`), agentsSchema);

export const getGatewayStatus = async (): Promise<GatewayStatus> =>
  parseResponse(axios.get(`${apiBase}/status/all`), statusSchema).then((res) => res.gateway);

export const getStatus = async (): Promise<StatusResponse> =>
  parseResponse(axios.get(`${apiBase}/status/all`), statusSchema);

export const getMetrics = async (): Promise<MetricPoint[]> =>
  parseResponse(axios.get(`${apiBase}/metrics`), metricsSchema);

export const startAgent = async (id: string): Promise<AgentInfo> =>
  parseResponse(axios.post(`${apiBase}/agents/${id}/start`), agentSchema);

export const stopAgent = async (id: string): Promise<AgentInfo> =>
  parseResponse(axios.post(`${apiBase}/agents/${id}/stop`), agentSchema);

export const restartGateway = async (): Promise<{ ok: boolean }> => {
  const { data } = await axios.post(`${apiBase}/gateway/restart`);
  if (typeof data?.ok !== 'boolean') {
    throw new Error('Unexpected gateway response');
  }
  return data;
};

export const postCommand = async (text: string): Promise<CommandResponse> =>
  parseResponse(
    axios.post(`${apiBase}/command`, { text }),
    commandResponseSchema
  );
