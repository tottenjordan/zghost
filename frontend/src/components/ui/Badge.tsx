import { forwardRef } from 'react';
import type { HTMLAttributes } from 'react';
import { cn } from '../../lib/utils';

export interface BadgeProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'success' | 'warning' | 'error' | 'info';
}

export const Badge = forwardRef<HTMLDivElement, BadgeProps>(
  ({ className, variant = 'default', ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold',
        {
          'bg-zinc-700 text-zinc-100': variant === 'default',
          'bg-green-600 text-white': variant === 'success',
          'bg-yellow-600 text-white': variant === 'warning',
          'bg-red-600 text-white': variant === 'error',
          'bg-blue-600 text-white': variant === 'info',
        },
        className
      )}
      {...props}
    />
  )
);
Badge.displayName = 'Badge';
