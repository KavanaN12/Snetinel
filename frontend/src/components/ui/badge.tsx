import { cn } from '../../lib/utils';

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  tone?: 'default' | 'success' | 'warning' | 'danger';
}

export function Badge({ className, tone = 'default', ...props }: BadgeProps) {
  const tones = {
    default: 'bg-slate-800/80 text-slate-200',
    success: 'bg-emerald-500/15 text-emerald-300',
    warning: 'bg-amber-500/15 text-amber-300',
    danger: 'bg-rose-500/15 text-rose-300',
  };

  return <span className={cn('inline-flex items-center rounded-full border border-white/10 px-3 py-1 text-xs font-medium', tones[tone], className)} {...props} />;
}
