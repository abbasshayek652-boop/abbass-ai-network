import { useState } from 'react';
import { Button } from './ui/button';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';

interface TerminalProps {
  onRun: (command: string) => Promise<void>;
  busy?: boolean;
}

export const Terminal = ({ onRun, busy = false }: TerminalProps) => {
  const [input, setInput] = useState('');

  const run = async () => {
    if (!input.trim()) return;
    await onRun(input);
    setInput('');
  };

  return (
    <Card className="h-80">
      <CardHeader className="flex items-center justify-between">
        <CardTitle>Terminal</CardTitle>
        <Button onClick={run} disabled={busy || !input.trim()} className="px-6">
          RUN
        </Button>
      </CardHeader>
      <CardContent>
        <textarea
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="> Enter command e.g. deploy --agent crypto"
          className="h-56 w-full resize-none rounded-lg border border-[var(--neon)]/20 bg-[var(--panel2)]/80 p-3 text-xs text-[var(--text)] focus:outline-none focus:ring-2 focus:ring-[var(--neon)]"
        />
      </CardContent>
    </Card>
  );
};
