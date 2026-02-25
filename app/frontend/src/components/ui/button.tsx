import { type ButtonHTMLAttributes, forwardRef } from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cn } from '@/lib/utils';

type Variant = 'default' | 'ghost' | 'outline';

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  asChild?: boolean;
  variant?: Variant;
};

const variantMap: Record<Variant, string> = {
  default:
    'bg-[var(--neon)] text-black hover:bg-[var(--alert)] transition shadow-neon',
  ghost: 'bg-transparent border border-[var(--neon)]/40 hover:border-[var(--neon)]',
  outline:
    'border border-[var(--neon2)] text-[var(--neon2)] hover:bg-[var(--neon2)]/10'
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, asChild = false, variant = 'default', ...props }, ref) => {
    const Comp = asChild ? Slot : 'button';
    return (
      <Comp
        className={cn(
          'inline-flex items-center justify-center rounded-md px-4 py-2 text-sm font-semibold uppercase tracking-wide transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--neon)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--panel)]',
          variantMap[variant],
          className
        )}
        ref={ref as never}
        {...props}
      />
    );
  }
);

Button.displayName = 'Button';
