import type { HTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

interface ProgressProps extends HTMLAttributes<HTMLDivElement> {
  value: number;
}

export const Progress = ({ value, className, ...props }: ProgressProps) => (
  <div
    className={cn('h-2 w-full overflow-hidden rounded-full bg-[var(--panel2)]/80', className)}
    {...props}
  >
    <div
      className="h-full bg-gradient-to-r from-[var(--neon)] to-[var(--neon2)] transition-all"
      style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
    />
  </div>
);
