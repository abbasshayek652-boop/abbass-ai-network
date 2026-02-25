import * as React from 'react';
import * as RadixSwitch from '@radix-ui/react-switch';
import { cn } from '@/lib/utils';

export interface SwitchProps extends RadixSwitch.SwitchProps {}

export const Switch = React.forwardRef<
  HTMLButtonElement,
  SwitchProps
>(({ className, ...props }, ref) => (
  <RadixSwitch.Root
    ref={ref}
    className={cn(
      'relative h-5 w-10 rounded-full border border-[var(--neon)]/50 bg-[var(--panel2)] transition-colors data-[state=checked]:bg-[var(--neon)]/70',
      className
    )}
    {...props}
  >
    <RadixSwitch.Thumb className="block h-4 w-4 translate-x-0.5 rounded-full bg-white transition-transform data-[state=checked]:translate-x-[22px]" />
  </RadixSwitch.Root>
));

Switch.displayName = 'Switch';
