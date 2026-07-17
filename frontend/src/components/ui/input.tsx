import * as React from 'react';
import { cn } from '../../lib/utils';

export type InputProps = React.InputHTMLAttributes<HTMLInputElement>;

export const Input = React.forwardRef<HTMLInputElement, InputProps>(({ className, ...props }, ref) => {
  return (
    <input
      ref={ref}
      className={cn(
        'flex h-11 w-full rounded-xl border border-white/10 bg-slate-950/70 px-4 text-sm text-slate-100 outline-none ring-0 placeholder:text-slate-500 focus:border-cyan-400/60',
        className,
      )}
      {...props}
    />
  );
});

Input.displayName = 'Input';
