import { useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import type { AgentInfo, MetricPoint } from '@/types';
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

interface MetricsProps {
  metrics: MetricPoint[];
  gatewayOnline: boolean;
  agents: AgentInfo[];
}

const formatUptime = (seconds: number) => {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
};

export const Metrics = ({ metrics, gatewayOnline, agents }: MetricsProps) => {
  const latest = metrics.at(-1);
  const activeAgents = useMemo(() => agents.filter((agent) => agent.status === 'running').length, [agents]);

  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      <Card>
        <CardHeader>
          <CardTitle>Gateway</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-2xl font-bold text-[var(--neon)]">{gatewayOnline ? 'ONLINE' : 'OFFLINE'}</p>
          <p className="text-xs text-[var(--text-dim)]">Uptime window {latest ? formatUptime(latest.t) : '--:--'}</p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Active Agents</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-2xl font-bold text-[var(--neon2)]">{activeAgents}</p>
          <p className="text-xs text-[var(--text-dim)]">of {agents.length} registered</p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>CPU Load</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-2xl font-bold text-[var(--warn)]">{latest ? `${latest.cpu.toFixed(1)}%` : '--'}</p>
          <p className="text-xs text-[var(--text-dim)]">Gateway aggregate</p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>24h PnL</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-2xl font-bold text-[var(--alert)]">{latest ? `$${latest.pnl.toFixed(2)}` : '--'}</p>
          <p className="text-xs text-[var(--text-dim)]">Simulated paper performance</p>
        </CardContent>
      </Card>
      <Card className="col-span-full h-64">
        <CardHeader>
          <CardTitle>Resource Usage</CardTitle>
        </CardHeader>
        <CardContent className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={metrics}>
              <defs>
                <linearGradient id="cpuGradient" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="5%" stopColor="var(--neon)" stopOpacity={0.8} />
                  <stop offset="95%" stopColor="var(--neon)" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="memGradient" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="5%" stopColor="var(--neon2)" stopOpacity={0.8} />
                  <stop offset="95%" stopColor="var(--neon2)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="rgba(0,255,209,0.1)" strokeDasharray="4 4" />
              <XAxis dataKey="t" stroke="var(--text-dim)" tickFormatter={(t) => `${Math.round(t)}s`} />
              <YAxis stroke="var(--text-dim)" domain={[0, 100]} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#0A0D14',
                  borderColor: 'rgba(0,255,209,0.3)',
                  color: 'var(--text)'
                }}
              />
              <Area type="monotone" dataKey="cpu" stroke="var(--neon)" fill="url(#cpuGradient)" />
              <Area type="monotone" dataKey="mem" stroke="var(--neon2)" fill="url(#memGradient)" />
            </AreaChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  );
};
