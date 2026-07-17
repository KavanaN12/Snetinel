import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(value?: string | null) {
  if (!value) return '—';
  return new Date(value).toLocaleString('en', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

export function getSeverityTone(severity: string) {
  switch (severity.toLowerCase()) {
    case 'critical':
      return 'bg-rose-500/15 text-rose-300 border-rose-500/30';
    case 'high':
      return 'bg-amber-500/15 text-amber-300 border-amber-500/30';
    case 'medium':
      return 'bg-sky-500/15 text-sky-300 border-sky-500/30';
    default:
      return 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30';
  }
}
