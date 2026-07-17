import { AlertTriangle } from 'lucide-react';
import { Button } from '../ui/button';

export function ErrorState({ message, onRetry }: { message?: string; onRetry?: () => void }) {
  return (
    <div className="flex min-h-[40vh] items-center justify-center">
      <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-8 text-center text-slate-200">
        <AlertTriangle className="mx-auto mb-3 h-8 w-8 text-rose-400" />
        <p className="mb-3 font-medium">Unable to load the requested data.</p>
        <p className="mb-5 text-sm text-slate-400">{message ?? 'The backend may be unavailable or the workspace has no data yet.'}</p>
        {onRetry ? <Button onClick={onRetry}>Retry</Button> : null}
      </div>
    </div>
  );
}
