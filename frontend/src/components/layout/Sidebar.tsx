import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  TrendingUp,
  Workflow,
  Star,
  Film,
  FileText,
  Mic,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { cn } from '../../lib/utils';

const navItems = [
  { path: '/trends', icon: TrendingUp, label: 'Trends', step: 1 },
  { path: '/rating', icon: Star, label: 'Rating', step: 2 },
  { path: '/orchestration', icon: Workflow, label: 'Orchestration', step: 3 },
  { path: '/narrative', icon: FileText, label: 'Narrative', step: null },
  { path: '/studio', icon: Film, label: 'AV Studio', step: null },
  { path: '/voice', icon: Mic, label: 'Voice Assistant', step: null },
];

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();

  return (
    <aside
      className={cn(
        'flex h-full flex-col border-r border-zinc-800/60 bg-zinc-900/95 transition-all duration-300 ease-in-out',
        collapsed ? 'w-16' : 'w-60'
      )}
    >
      <div className="flex h-14 items-center justify-end border-b border-zinc-800/60 px-3">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="rounded-lg p-1.5 text-zinc-500 transition-colors hover:bg-zinc-800 hover:text-zinc-300"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </button>
      </div>

      <nav className="flex-1 space-y-0.5 p-2">
        {navItems.map(({ path, icon: Icon, label, step }) => {
          const isActive = location.pathname === path;
          return (
            <Link
              key={path}
              to={path}
              className={cn(
                'group relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200',
                isActive
                  ? 'bg-blue-600/15 text-blue-400 shadow-sm'
                  : 'text-zinc-500 hover:bg-zinc-800/70 hover:text-zinc-200'
              )}
              title={collapsed ? label : undefined}
            >
              {isActive && (
                <div className="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-r-full bg-blue-500" />
              )}
              {!collapsed && step !== null && (
                <span className="flex h-4 w-4 items-center justify-center rounded-full bg-zinc-800 text-[10px] font-semibold text-zinc-400">
                  {step}
                </span>
              )}
              <Icon className={cn(
                'h-[18px] w-[18px] flex-shrink-0 transition-colors',
                isActive ? 'text-blue-400' : 'text-zinc-500 group-hover:text-zinc-300'
              )} />
              {!collapsed && <span className="truncate">{label}</span>}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
