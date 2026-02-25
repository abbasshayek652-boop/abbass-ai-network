import { useCallback, useEffect, useMemo, useState } from 'react';
import { AgentList } from './AgentList';
import { LogsPanel } from './LogsPanel';
import { Terminal } from './Terminal';
import { Metrics } from './Metrics';
import { Card, CardContent } from './ui/card';
import { Button } from './ui/button';
import { Switch } from './ui/switch';
import { Badge } from './ui/badge';
import { FlameIcon, RefreshCwIcon, SignalIcon } from 'lucide-react';
import { motion } from 'framer-motion';
import { toast } from 'sonner';
import {
  getStatus,
  getMetrics,
  startAgent,
  stopAgent,
  restartGateway,
  postCommand
} from '@/lib/api';
import { statusSocket } from '@/lib/ws';
import type { AgentInfo, GatewayStatus, MetricPoint, WsEvent } from '@/types';

const formatTimestamp = () => new Date().toLocaleString();

export const CyberConsoleDashboard = () => {
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [gateway, setGateway] = useState<GatewayStatus>({ online: true, uptime_s: 0 });
  const [metrics, setMetrics] = useState<MetricPoint[]>([]);
  const [logs, setLogs] = useState<string[]>([]);
  const [timestamp, setTimestamp] = useState(() => formatTimestamp());
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);
  const [loadingAgent, setLoadingAgent] = useState<string | null>(null);
  const [terminalBusy, setTerminalBusy] = useState(false);
  const [gatewayPending, setGatewayPending] = useState(false);

  const appendLog = useCallback((line: string) => {
    setLogs((prev) => [...prev.slice(-199), line]);
  }, []);

  const refresh = useCallback(async () => {
    try {
      const status = await getStatus();
      setAgents(status.agents);
      setGateway(status.gateway);
      appendLog(`[${new Date().toLocaleTimeString()}] Status synchronised`);
    } catch (error) {
      console.error(error);
      toast.error('Failed to refresh status');
    }
    try {
      const latestMetrics = await getMetrics();
      setMetrics(latestMetrics);
    } catch (error) {
      console.error(error);
    }
  }, [appendLog]);

  useEffect(() => {
    refresh();
    const id = setInterval(() => setTimestamp(formatTimestamp()), 1_000);
    const metricsInterval = setInterval(() => {
      getMetrics()
        .then(setMetrics)
        .catch((error) => console.error('metrics refresh failed', error));
    }, 10_000);

    const onEvent = (event: WsEvent) => {
      if (event.type === 'log') {
        appendLog(event.line);
      } else if (event.type === 'agent') {
        setAgents((prev) =>
          prev.map((agent) =>
            agent.id === event.id
              ? { ...agent, cpu: event.cpu, mem: event.mem, status: event.status }
              : agent
          )
        );
      } else if (event.type === 'gateway') {
        setGateway((prev) => ({ ...prev, online: event.online }));
      }
    };

    statusSocket.addListener(onEvent);
    statusSocket.connect();

    return () => {
      clearInterval(id);
      clearInterval(metricsInterval);
      statusSocket.removeListener(onEvent);
      statusSocket.disconnect();
    };
  }, [appendLog, refresh]);

  const onlineAgents = useMemo(() => agents.filter((agent) => agent.status === 'running'), [agents]);

  const handleStart = useCallback(
    async (id: string) => {
      setLoadingAgent(id);
      setAgents((prev) =>
        prev.map((agent) => (agent.id === id ? { ...agent, status: 'running' } : agent))
      );
      try {
        const updated = await startAgent(id);
        setAgents((prev) => prev.map((agent) => (agent.id === id ? updated : agent)));
        appendLog(`[${new Date().toLocaleTimeString()}] Started agent ${id}`);
        toast.success(`Agent ${id} started`);
      } catch (error) {
        console.error(error);
        toast.error(`Failed to start agent ${id}`);
        refresh();
      } finally {
        setLoadingAgent(null);
      }
    },
    [appendLog, refresh]
  );

  const handleStop = useCallback(
    async (id: string) => {
      setLoadingAgent(id);
      setAgents((prev) =>
        prev.map((agent) => (agent.id === id ? { ...agent, status: 'stopped' } : agent))
      );
      try {
        const updated = await stopAgent(id);
        setAgents((prev) => prev.map((agent) => (agent.id === id ? updated : agent)));
        appendLog(`[${new Date().toLocaleTimeString()}] Stopped agent ${id}`);
        toast.success(`Agent ${id} stopped`);
      } catch (error) {
        console.error(error);
        toast.error(`Failed to stop agent ${id}`);
        refresh();
      } finally {
        setLoadingAgent(null);
      }
    },
    [appendLog, refresh]
  );

  const handleRestartGateway = useCallback(async () => {
    setGatewayPending(true);
    setGateway((prev) => ({ ...prev, online: false }));
    appendLog(`[${new Date().toLocaleTimeString()}] Gateway restart initiated`);
    try {
      await restartGateway();
      await new Promise((resolve) => setTimeout(resolve, 1500));
      await refresh();
      toast.success('Gateway restart complete');
    } catch (error) {
      console.error(error);
      toast.error('Gateway restart failed');
    } finally {
      setGatewayPending(false);
    }
  }, [refresh, appendLog]);

  const handleCommand = useCallback(
    async (command: string) => {
      setTerminalBusy(true);
      appendLog(`$ ${command}`);
      const agentMatch = command.match(/--agent\s+(\w+)/i);
      if (agentMatch) {
        appendLog(`Routing to agent: ${agentMatch[1]}`);
      }
      try {
        const response = await postCommand(command);
        appendLog(response.message);
        if (!response.ok) {
          toast.warning('Command responded with warning');
        }
      } catch (error) {
        console.error(error);
        toast.error('Command failed');
      } finally {
        setTerminalBusy(false);
      }
    },
    [appendLog]
  );

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6">
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-[var(--neon)]/20 bg-[var(--panel)]/80 p-4 shadow-neon"
      >
        <div>
          <h1 className="text-2xl font-bold text-[var(--neon)]">Mother AI Cyber Console</h1>
          <p className="text-xs text-[var(--text-dim)]">{timestamp}</p>
        </div>
        <div className="flex items-center gap-4 text-xs">
          <Badge variant={gateway.online ? 'success' : 'danger'}>
            {gateway.online ? 'ONLINE' : 'OFFLINE'}
          </Badge>
          <div className="flex items-center gap-2 text-[var(--text-dim)]">
            <span>Notifications</span>
            <Switch
              checked={notificationsEnabled}
              onCheckedChange={(value) => setNotificationsEnabled(Boolean(value))}
            />
          </div>
          <Button onClick={refresh} disabled={gatewayPending} variant="outline">
            <RefreshCwIcon className="mr-2 h-4 w-4" /> Refresh
          </Button>
        </div>
      </motion.div>

      <div className="grid gap-6 lg:grid-cols-[300px_minmax(0,1fr)]">
        <AgentList
          agents={agents}
          onStart={handleStart}
          onStop={handleStop}
          loadingAgentId={loadingAgent}
          gatewayOnline={gateway.online && !gatewayPending}
        />
        <div className="space-y-6">
          <Metrics metrics={metrics} gatewayOnline={gateway.online} agents={agents} />

          <Card className="grid gap-4 md:grid-cols-2">
            <CardContent className="flex flex-col gap-3">
              <h3 className="text-sm font-semibold uppercase text-[var(--text-dim)]">Gateway Controls</h3>
              <p className="text-xs text-[var(--text-dim)]">
                Manage uptime, restart workflows, and monitor active agent utilisation.
              </p>
              <div className="flex flex-wrap gap-2">
                <Button onClick={handleRestartGateway} disabled={gatewayPending}>
                  <SignalIcon className="mr-2 h-4 w-4" /> Restart Gateway
                </Button>
              </div>
              <div className="text-xs text-[var(--text-dim)]">
                Active Agents: <span className="text-[var(--alert)]">{onlineAgents.length}</span>
              </div>
            </CardContent>
            <CardContent className="flex flex-col justify-center gap-2 rounded-xl border border-[var(--neon)]/10 bg-[var(--panel2)]/70">
              <div className="flex items-center gap-2 text-sm text-[var(--text-dim)]">
                <FlameIcon className="h-4 w-4 text-[var(--neon2)]" />
                System load
              </div>
              <p className="text-3xl font-semibold text-[var(--neon2)]">
                {metrics.at(-1)?.cpu.toFixed(1) ?? '--'}%
              </p>
              <p className="text-xs text-[var(--text-dim)]">Monitoring aggregated CPU from all venues.</p>
            </CardContent>
          </Card>

          <div className="grid gap-6 md:grid-cols-2">
            <LogsPanel lines={logs} />
            <Terminal onRun={handleCommand} busy={terminalBusy} />
          </div>
        </div>
      </div>
    </div>
  );
};
