import { Bell, Menu, Search, SunMoon } from 'lucide-react';
import { useLocation } from 'react-router-dom';
import { useAuthStore } from '../../store/auth';
import { useThemeStore } from '../../store/theme';
import { Button } from '../ui/button';
import { Input } from '../ui/input';

export function Navbar({ onMenuToggle }: { onMenuToggle: () => void }) {
  const location = useLocation();
  const user = useAuthStore((state) => state.user);
  const theme = useThemeStore((state) => state.theme);
  const toggleTheme = useThemeStore((state) => state.toggleTheme);

  const breadcrumb = location.pathname
    .split('/')
    .filter(Boolean)
    .map((segment) => segment.replace('-', ' '))
    .join(' / ');

  return (
    <header className="flex items-center justify-between border-b border-white/10 bg-slate-950/60 px-4 py-4 backdrop-blur xl:px-6">
      <div className="flex items-center gap-3">
        <Button variant="secondary" size="sm" className="xl:hidden" onClick={onMenuToggle}>
          <Menu className="h-4 w-4" />
        </Button>
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-cyan-400">Mission control</p>
          <p className="text-sm text-slate-400">{breadcrumb || 'dashboard'}</p>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <label className="hidden items-center gap-2 rounded-full border border-white/10 bg-slate-900/60 px-3 py-2 text-sm text-slate-400 md:flex">
          <Search className="h-4 w-4" />
          <Input className="h-8 w-40 border-0 bg-transparent p-0 text-sm" placeholder="Search" />
        </label>
        <Button variant="secondary" size="sm" onClick={toggleTheme}>
          <SunMoon className="h-4 w-4" />
        </Button>
        <div className="rounded-full border border-white/10 bg-slate-900/60 p-2 text-slate-300">
          <Bell className="h-4 w-4" />
        </div>
        <div className="flex items-center gap-3 rounded-full border border-cyan-400/20 bg-cyan-500/10 px-3 py-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-cyan-400/20 text-sm font-semibold text-cyan-200">
            {user?.email?.[0]?.toUpperCase() ?? 'U'}
          </div>
          <div className="hidden md:block">
            <p className="text-sm font-medium text-slate-100">{user?.email ?? 'Operator'}</p>
            <p className="text-xs text-slate-400">{theme === 'dark' ? 'Dark mode' : 'Light mode'}</p>
          </div>
        </div>
      </div>
    </header>
  );
}
