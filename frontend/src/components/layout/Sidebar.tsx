import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  Settings,
  Workflow,
  Star,
  Film,
  FileText,
  ChevronLeft,
  ChevronRight,
  Blocks,
} from 'lucide-react';
import { cn } from '../../lib/utils';

const navItems = [
  { path: '/trends', icon: Settings, label: 'Configure' },
  { path: '/orchestration', icon: Workflow, label: 'Orchestration' },
  { path: '/narrative', icon: FileText, label: 'Narrative' },
  { path: '/studio', icon: Film, label: 'AV Studio' },
  { path: '/rating', icon: Star, label: 'Evaluation Studio' },
  { path: '/skills', icon: Blocks, label: 'Skills' },
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
        {navItems.map(({ path, icon: Icon, label }) => {
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
