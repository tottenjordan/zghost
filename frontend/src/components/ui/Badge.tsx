import { forwardRef } from 'react';
import type { HTMLAttributes } from 'react';
import { cn } from '../../lib/utils';

export interface BadgeProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'success' | 'warning' | 'error' | 'danger' | 'info';
}

export const Badge = forwardRef<HTMLDivElement, BadgeProps>(
  ({ className, variant = 'default', ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        'inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium tracking-wide',
        {
          'bg-zinc-800 text-zinc-300 ring-1 ring-zinc-700': variant === 'default',
          'bg-emerald-500/15 text-emerald-400 ring-1 ring-emerald-500/30': variant === 'success',
          'bg-amber-500/15 text-amber-400 ring-1 ring-amber-500/30': variant === 'warning',
          'bg-red-500/15 text-red-400 ring-1 ring-red-500/30': variant === 'error' || variant === 'danger',
          'bg-blue-500/15 text-blue-400 ring-1 ring-blue-500/30': variant === 'info',
        },
        className
      )}
      {...props}
    />
  )
);
Badge.displayName = 'Badge';
