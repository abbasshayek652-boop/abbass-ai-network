import { useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';

interface LogsPanelProps {
  lines: string[];
}

export const LogsPanel = ({ lines }: LogsPanelProps) => {
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const node = ref.current;
    if (node) {
      node.scrollTop = node.scrollHeight;
    }
  }, [lines]);

  return (
    <Card className="h-80">
      <CardHeader>
        <CardTitle>Logs</CardTitle>
      </CardHeader>
      <CardContent>
        <div
          ref={ref}
          className="scrollbar-thin h-60 overflow-y-auto whitespace-pre-wrap text-xs text-[var(--text-dim)]"
        >
          {lines.length === 0 ? <span>No logs yet.</span> : lines.map((line, idx) => <div key={`${line}-${idx}`}>{line}</div>)}
        </div>
      </CardContent>
    </Card>
  );
};
