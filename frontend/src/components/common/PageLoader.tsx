import { Loader2 } from 'lucide-react';

export function PageLoader() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <div className="flex items-center gap-3 rounded-full border border-white/10 bg-slate-900/70 px-5 py-3 text-slate-300 shadow-lg backdrop-blur">
        <Loader2 className="h-5 w-5 animate-spin text-cyan-400" />
        Syncing with Sentinel APIs…
      </div>
    </div>
  );
}
