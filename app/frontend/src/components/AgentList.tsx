import { memo } from 'react';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Progress } from './ui/progress';
import type { AgentInfo } from '@/types';
import { cn } from '@/lib/utils';
import { PowerIcon, SquareIcon } from 'lucide-react';

interface AgentListProps {
  agents: AgentInfo[];
  onStart: (id: string) => void;
  onStop: (id: string) => void;
  loadingAgentId?: string | null;
  gatewayOnline: boolean;
}

const statusBadge = (status: AgentInfo['status']) => {
  switch (status) {
    case 'running':
      return <Badge variant="success">RUNNING</Badge>;
    case 'idle':
      return <Badge variant="warning">IDLE</Badge>;
    default:
      return <Badge variant="danger">STOPPED</Badge>;
  }
};

export const AgentList = memo<AgentListProps>(function AgentList({
  agents,
  onStart,
  onStop,
  loadingAgentId,
  gatewayOnline
}) {
  return (
    <Card className="space-y-3">
      <CardHeader className="flex flex-col items-start gap-2">
        <CardTitle>Agents</CardTitle>
        <p className="text-xs text-[var(--text-dim)]">Fleet overview and quick controls.</p>
      </CardHeader>
      <CardContent className="space-y-3">
        {agents.map((agent) => {
          const isLoading = loadingAgentId === agent.id;
          return (
            <div
              key={agent.id}
              className="flex items-center justify-between rounded-lg border border-[var(--neon)]/10 bg-[var(--panel2)]/70 p-3"
            >
              <div className="flex flex-col gap-2">
                <div className="flex items-center gap-3">
                  <span className="text-sm font-semibold text-[var(--neon)]">{agent.name}</span>
                  {statusBadge(agent.status)}
                </div>
                <div className="flex items-center gap-3 text-[10px] text-[var(--text-dim)]">
                  <span className="w-16">CPU</span>
                  <Progress value={agent.cpu} className="w-32" />
                  <span>{agent.cpu}%</span>
                </div>
                <div className="flex items-center gap-3 text-[10px] text-[var(--text-dim)]">
                  <span className="w-16">MEM</span>
                  <Progress value={agent.mem} className="w-32" />
                  <span>{agent.mem}%</span>
                </div>
              </div>
              <div className="flex gap-2">
                <Button
                  variant="ghost"
                  className={cn(
                    'border border-[var(--alert)]/50 text-[var(--alert)] hover:bg-[var(--alert)]/10',
                    (!gatewayOnline || agent.status === 'running') && 'opacity-40'
                  )}
                  disabled={isLoading || !gatewayOnline || agent.status === 'running'}
                  onClick={() => onStart(agent.id)}
                >
                  <PowerIcon className="mr-2 h-4 w-4" /> Start
                </Button>
                <Button
                  variant="ghost"
                  className={cn(
                    'border border-[var(--danger)]/60 text-[var(--danger)] hover:bg-[var(--danger)]/10',
                    (!gatewayOnline || agent.status === 'stopped') && 'opacity-40'
                  )}
                  disabled={isLoading || !gatewayOnline || agent.status === 'stopped'}
                  onClick={() => onStop(agent.id)}
                >
                  <SquareIcon className="mr-2 h-4 w-4" /> Stop
                </Button>
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
});
