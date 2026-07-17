import { Compass, LayoutDashboard, LogOut, Radar, ScanSearch, Settings, ShieldCheck, Sparkles, BookOpenText, ScrollText, TrendingUp, Waves } from 'lucide-react';
import { NavLink } from 'react-router-dom';
import { useAuthStore } from '../../store/auth';
import { cn } from '../../lib/utils';

const links = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/discovery', label: 'Cloud Discovery', icon: Compass },
  { to: '/attack-paths', label: 'Attack Paths', icon: Radar },
  { to: '/findings', label: 'Findings', icon: ScanSearch },
  { to: '/compliance', label: 'Compliance', icon: ShieldCheck },
  { to: '/drift', label: 'Drift Detection', icon: Waves },
  { to: '/rag', label: 'RAG KB', icon: BookOpenText },
  { to: '/audit', label: 'Audit Logs', icon: ScrollText },
  { to: '/settings', label: 'Settings', icon: Settings },
];

export function Sidebar({ collapsed = false, onClose }: { collapsed?: boolean; onClose?: () => void }) {
  const logout = useAuthStore((state) => state.logout);

  return (
    <aside className={cn('flex h-full flex-col border-r border-white/10 bg-slate-950/80 p-4 backdrop-blur-xl', collapsed ? 'w-20' : 'w-72')}>
      <div className="mb-8 flex items-center gap-3 rounded-2xl border border-cyan-400/20 bg-cyan-500/10 px-3 py-3">
        <div className="rounded-xl bg-cyan-500/15 p-2 text-cyan-300">
          <Sparkles className="h-5 w-5" />
        </div>
        {!collapsed ? <div><p className="text-sm font-semibold text-slate-100">Sentinel</p><p className="text-xs text-slate-400">Cloud defense OS</p></div> : null}
      </div>

      <nav className="flex-1 space-y-1">
        {links.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            onClick={onClose}
            className={({ isActive }) => cn('flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition', isActive ? 'bg-cyan-500/15 text-cyan-200' : 'text-slate-400 hover:bg-slate-800/70 hover:text-slate-100')}
          >
            <Icon className="h-4 w-4" />
            {!collapsed ? <span>{label}</span> : null}
          </NavLink>
        ))}
      </nav>

      <div className="mt-4 rounded-2xl border border-white/10 bg-slate-900/70 p-3">
        <div className="mb-3 flex items-center gap-3">
          <div className="rounded-full bg-emerald-500/15 p-2 text-emerald-300">
            <TrendingUp className="h-4 w-4" />
          </div>
          {!collapsed ? <div><p className="text-sm font-medium text-slate-200">Threat posture</p><p className="text-xs text-slate-400">Elevated visibility</p></div> : null}
        </div>
        {!collapsed ? (
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Runtime integrity</span>
            <span className="text-emerald-300">97%</span>
          </div>
        ) : null}
      </div>

      <button onClick={logout} className="mt-4 flex items-center gap-3 rounded-xl border border-white/10 px-3 py-2 text-sm text-slate-400 transition hover:bg-slate-800/70 hover:text-slate-100">
        <LogOut className="h-4 w-4" />
        {!collapsed ? 'Sign out' : null}
      </button>
    </aside>
  );
}
