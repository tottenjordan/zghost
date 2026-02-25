import { Plus, X } from 'lucide-react';
import { cn } from '../../lib/utils';
import type { PipelineSession } from '../../stores/campaignStore';

interface SessionTabBarProps {
  sessions: PipelineSession[];
  activeSessionIndex: number;
  onSelectSession: (index: number) => void;
  onRemoveSession: (sessionId: string) => void;
  onNewSession: () => void;
  isRunning: boolean;
}

export function SessionTabBar({
  sessions,
  activeSessionIndex,
  onSelectSession,
  onRemoveSession,
  onNewSession,
  isRunning,
}: SessionTabBarProps) {
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

  return (
    <div className="flex items-center gap-2 p-2 bg-zinc-900/50 border border-zinc-800 rounded-lg overflow-x-auto">
      {sessions.map((session, index) => {
        const isActive = index === activeSessionIndex;
        const canRemove = session.status === 'completed' || session.status === 'error';

        return (
          <button
            key={session.id}
            onClick={() => onSelectSession(index)}
            className={cn(
              'flex items-center gap-2 px-3 py-1.5 rounded-full text-xs transition-all whitespace-nowrap',
              isActive
                ? 'bg-zinc-700 ring-2 ring-blue-500 text-white'
                : 'bg-zinc-800 hover:bg-zinc-700 text-zinc-300'
            )}
          >
            <span>{session.label}</span>
            <div className={cn('w-2 h-2 rounded-full', getStatusColor(session.status))} />
            {canRemove && (
              <X
                className="w-3 h-3 hover:text-red-400 transition-colors"
                onClick={(e) => {
                  e.stopPropagation();
                  onRemoveSession(session.sessionId);
                }}
              />
            )}
          </button>
        );
      })}

      <button
        onClick={onNewSession}
        disabled={isRunning}
        className="flex items-center gap-1 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 disabled:bg-zinc-700 disabled:cursor-not-allowed text-white text-xs rounded-full transition-colors"
        title="Start a new pipeline run"
      >
        <Plus className="w-3 h-3" />
      </button>
    </div>
  );
}
