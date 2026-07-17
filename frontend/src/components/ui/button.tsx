import * as React from 'react';
import { cn } from '../../lib/utils';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'secondary' | 'ghost';
  size?: 'default' | 'sm' | 'lg';
}

export function Button({
  className,
  variant = 'default',
  size = 'default',
  ...props
}: ButtonProps) {
  const variants = {
    default: 'bg-cyan-500/90 text-slate-950 hover:bg-cyan-400',
    secondary: 'bg-slate-800/70 text-slate-100 hover:bg-slate-700',
    ghost: 'bg-transparent text-slate-300 hover:bg-slate-800/70',
  };
  const sizes = {
    default: 'h-10 px-4 py-2',
    sm: 'h-9 px-3 text-sm',
    lg: 'h-11 px-5',
  };

  return (
    <button
      className={cn(
        'inline-flex items-center justify-center rounded-xl border border-white/10 font-medium transition-all duration-200 disabled:pointer-events-none disabled:opacity-50',
        variants[variant],
        sizes[size],
        className,
      )}
      {...props}
    />
  );
}
