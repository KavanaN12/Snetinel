import { Link } from 'react-router-dom';

export function NotFoundPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 px-4 text-slate-200">
      <div className="w-full max-w-md rounded-2xl border border-white/10 bg-slate-900/80 p-8 text-center shadow-2xl">
        <p className="text-sm uppercase tracking-[0.25em] text-cyan-400">404</p>
        <h1 className="mt-3 text-2xl font-semibold text-white">This page is unavailable</h1>
        <p className="mt-3 text-sm text-slate-400">The route you requested does not exist or is no longer active.</p>
        <Link className="mt-6 inline-flex rounded-xl bg-cyan-500/90 px-4 py-2 text-sm font-medium text-slate-950" to="/dashboard">
          Go to dashboard
        </Link>
      </div>
    </div>
  );
}
