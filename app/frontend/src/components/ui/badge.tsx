import type { HTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

type BadgeVariant = 'default' | 'success' | 'danger' | 'warning';

const map: Record<BadgeVariant, string> = {
  default: 'border-[var(--neon2)] text-[var(--neon2)]',
  success: 'border-[var(--alert)] text-[var(--alert)]',
  danger: 'border-[var(--danger)] text-[var(--danger)]',
  warning: 'border-[var(--warn)] text-[var(--warn)]'
};

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
}

export const Badge = ({ className, variant = 'default', ...props }: BadgeProps) => (
  <span
    className={cn(
      'inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.2em]',
      map[variant],
      className
    )}
    {...props}
  />
);
