import { useRef, useState, useEffect } from 'react';
import { Plus, X, Copy, ChevronLeft, ChevronRight } from 'lucide-react';
import { cn } from '../../lib/utils';
import type { PipelineSession } from '../../stores/campaignStore';

interface SessionTabBarProps {
  sessions: PipelineSession[];
  activeSessionIndex: number;
  onSelectSession: (index: number) => void;
  onRemoveSession: (sessionId: string) => void;
  onDuplicate?: (session: PipelineSession) => void;
  onNewSession: () => void;
  isRunning: boolean;
}

export function SessionTabBar({
  sessions,
  activeSessionIndex,
  onSelectSession,
  onRemoveSession,
  onDuplicate,
  onNewSession,
  isRunning,
}: SessionTabBarProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);

  const getStatusColor = (status: PipelineSession['status']) => {
    switch (status) {
      case 'running':
        return 'bg-green-500';
      case 'completed':
        return 'bg-zinc-500';
      case 'error':
        return 'bg-red-500';
      case 'idle':
      default:
        return 'bg-zinc-600';
    }
  };

  const getStatusLabel = (status: PipelineSession['status']) => {
    switch (status) {
      case 'running':
        return 'Running';
      case 'completed':
        return 'Done';
      case 'error':
        return 'Error';
      default:
        return 'Idle';
    }
  };

  const updateScrollState = () => {
    const el = scrollRef.current;
    if (!el) return;
    setCanScrollLeft(el.scrollLeft > 0);
    setCanScrollRight(el.scrollLeft + el.clientWidth < el.scrollWidth - 1);
  };

  useEffect(() => {
    updateScrollState();
    const el = scrollRef.current;
    if (el) {
      el.addEventListener('scroll', updateScrollState);
      const resizeObs = new ResizeObserver(updateScrollState);
      resizeObs.observe(el);
      return () => {
        el.removeEventListener('scroll', updateScrollState);
        resizeObs.disconnect();
      };
    }
  }, [sessions.length]);

  const scroll = (direction: 'left' | 'right') => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollBy({ left: direction === 'left' ? -200 : 200, behavior: 'smooth' });
  };

  if (sessions.length === 0) {
    return (
      <div className="flex items-center gap-2 p-2 bg-zinc-900/50 border border-zinc-800 rounded-lg">
        <span className="text-xs text-zinc-500">No active sessions</span>
        <button
          onClick={onNewSession}
          disabled={isRunning}
          className="flex items-center gap-1 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 disabled:bg-zinc-700 disabled:cursor-not-allowed text-white text-xs rounded transition-colors"
          title="Start a new pipeline run"
        >
          <Plus className="w-3 h-3" />
          New Run
        </button>
      </div>
    );
  }

  const showArrows = canScrollLeft || canScrollRight;

  return (
    <div className="flex items-center gap-1 p-1.5 bg-zinc-900/50 border border-zinc-800 rounded-lg">
      {/* Session count badge */}
      <span className="flex-shrink-0 px-2 py-1 text-[10px] font-medium text-zinc-500 tabular-nums">
        {sessions.length} run{sessions.length !== 1 ? 's' : ''}
      </span>

      {/* Left scroll arrow */}
      {showArrows && (
        <button
          onClick={() => scroll('left')}
          disabled={!canScrollLeft}
          className="flex-shrink-0 p-1 rounded hover:bg-zinc-700 disabled:opacity-0 transition-opacity text-zinc-400"
        >
          <ChevronLeft className="w-3.5 h-3.5" />
        </button>
      )}

      {/* Scrollable session list */}
      <div
        ref={scrollRef}
        className="flex items-center gap-1.5 overflow-x-auto scrollbar-hide flex-1 min-w-0"
        style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
      >
        {sessions.map((session, index) => {
          const isActive = index === activeSessionIndex;
          const canRemove = session.status === 'completed' || session.status === 'error';

          return (
            <button
              key={session.id}
              onClick={() => onSelectSession(index)}
              className={cn(
                'group flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs transition-all whitespace-nowrap flex-shrink-0',
                isActive
                  ? 'bg-zinc-700 ring-1 ring-blue-500/60 text-white'
                  : 'bg-zinc-800/70 hover:bg-zinc-700/70 text-zinc-400 hover:text-zinc-200'
              )}
            >
              <div className={cn('w-1.5 h-1.5 rounded-full flex-shrink-0', getStatusColor(session.status))} />
              <span className="truncate max-w-[120px]">{session.label}</span>
              <span className={cn(
                'text-[10px] tabular-nums',
                isActive ? 'text-zinc-400' : 'text-zinc-600'
              )}>
                {getStatusLabel(session.status)}
              </span>
              {canRemove && onDuplicate && (
                <Copy
                  className="w-3 h-3 opacity-0 group-hover:opacity-100 hover:text-blue-400 transition-all"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDuplicate(session);
                  }}
                  title="Duplicate run with same config"
                />
              )}
              {canRemove && (
                <X
                  className="w-3 h-3 opacity-0 group-hover:opacity-100 hover:text-red-400 transition-all"
                  onClick={(e) => {
                    e.stopPropagation();
                    if (window.confirm(`Delete "${session.label}"? This cannot be undone.`)) {
                      onRemoveSession(session.sessionId);
                    }
                  }}
                  title="Delete run"
                />
              )}
            </button>
          );
        })}
      </div>

      {/* Right scroll arrow */}
      {showArrows && (
        <button
          onClick={() => scroll('right')}
          disabled={!canScrollRight}
          className="flex-shrink-0 p-1 rounded hover:bg-zinc-700 disabled:opacity-0 transition-opacity text-zinc-400"
        >
          <ChevronRight className="w-3.5 h-3.5" />
        </button>
      )}

      {/* New run button */}
      <button
        onClick={onNewSession}
        disabled={isRunning}
        className="flex-shrink-0 flex items-center gap-1 px-2.5 py-1 bg-blue-600 hover:bg-blue-700 disabled:bg-zinc-700 disabled:cursor-not-allowed text-white text-xs rounded-md transition-colors"
        title="Start a new pipeline run"
      >
        <Plus className="w-3 h-3" />
      </button>
    </div>
  );
}
