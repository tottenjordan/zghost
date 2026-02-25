import { forwardRef } from 'react';
import type { ButtonHTMLAttributes } from 'react';
import { cn } from '../../lib/utils';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          'inline-flex items-center justify-center rounded-lg font-medium transition-all duration-200',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-1 focus-visible:ring-offset-zinc-900',
          'disabled:pointer-events-none disabled:opacity-40',
          'active:scale-[0.98]',
          {
            'bg-blue-600 text-white hover:bg-blue-500 shadow-sm shadow-blue-600/25': variant === 'primary',
            'bg-zinc-800 text-zinc-200 hover:bg-zinc-700 ring-1 ring-zinc-700': variant === 'secondary',
            'hover:bg-zinc-800/80 text-zinc-300': variant === 'ghost',
            'bg-red-600 text-white hover:bg-red-500 shadow-sm shadow-red-600/25': variant === 'danger',
            'h-8 px-3 text-xs': size === 'sm',
            'h-9 px-4 text-sm': size === 'md',
            'h-11 px-6 text-base': size === 'lg',
          },
          className
        )}
        {...props}
      />
    );
  }
);

Button.displayName = 'Button';
