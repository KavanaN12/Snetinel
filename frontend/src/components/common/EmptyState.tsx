import { CircleSlash2 } from 'lucide-react';

export function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="flex min-h-[30vh] flex-col items-center justify-center rounded-2xl border border-dashed border-white/10 bg-slate-950/50 p-8 text-center text-slate-400">
      <CircleSlash2 className="mb-3 h-8 w-8 text-slate-500" />
      <p className="mb-1 text-lg font-semibold text-slate-200">{title}</p>
      <p className="max-w-md text-sm">{description}</p>
    </div>
  );
}
