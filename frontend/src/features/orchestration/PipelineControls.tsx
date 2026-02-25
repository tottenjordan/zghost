import { useState } from 'react';
import { Badge } from '../../components/ui/Badge';
import { Play, Square, RefreshCw, Activity, AlertTriangle } from 'lucide-react';
import { cn } from '../../lib/utils';

interface PipelineControlsProps {
  isRunning: boolean;
  sessionId: string | null;
  readyToLaunch: boolean;
  missingItems: string[];
  onStart: (parallelCount: number) => void;
  onStop: () => void;
  onRefresh: () => void;
}

export function PipelineControls({
  isRunning,
  sessionId,
  readyToLaunch,
  missingItems,
  onStart,
  onStop,
  onRefresh,
}: PipelineControlsProps) {
  const [parallelCount, setParallelCount] = useState(1);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-4 p-4 bg-zinc-900 border border-zinc-800 rounded-lg">
        {/* Session indicator */}
        <div className="flex items-center gap-2 flex-1">
          <Activity className={cn('w-4 h-4', isRunning && 'text-green-400 animate-pulse')} />
          <span className="text-sm text-zinc-400">Session:</span>
          {sessionId ? (
            <Badge variant="info" className="font-mono text-xs">
              {sessionId.slice(0, 8)}
            </Badge>
          ) : (
            <Badge variant="default" className="text-xs">
              None
            </Badge>
          )}
        </div>

        {/* Parallel stream count selector */}
        <div className="flex items-center gap-2">
          <label htmlFor="parallel-count" className="text-sm text-zinc-400">
            Parallel streams:
          </label>
          <select
            id="parallel-count"
            value={parallelCount}
            onChange={(e) => setParallelCount(Number(e.target.value))}
            disabled={isRunning}
            className="px-3 py-1 text-sm bg-zinc-800 border border-zinc-700 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {[1, 2, 3, 4, 5].map((count) => (
              <option key={count} value={count}>
                {count}
              </option>
            ))}
          </select>
        </div>

        {/* Control buttons */}
        <div className="flex items-center gap-2">
          {!isRunning ? (
            <button
              onClick={() => onStart(parallelCount)}
              disabled={isRunning || !readyToLaunch}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-zinc-700 disabled:cursor-not-allowed text-white text-sm rounded transition-colors"
              title={!readyToLaunch ? `Missing: ${missingItems.join(', ')}` : 'Start the pipeline'}
            >
              <Play className="w-4 h-4" />
              Start Pipeline
            </button>
          ) : (
            <button
              onClick={onStop}
              className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm rounded transition-colors"
            >
              <Square className="w-4 h-4" />
              Stop
            </button>
          )}

          <button
            onClick={onRefresh}
            disabled={isRunning}
            className="flex items-center gap-2 px-4 py-2 bg-zinc-700 hover:bg-zinc-600 disabled:bg-zinc-800 disabled:cursor-not-allowed text-white text-sm rounded transition-colors"
            title="Refresh status"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Validation warnings */}
      {!readyToLaunch && !isRunning && missingItems.length > 0 && (
        <div className="flex items-start gap-2 p-3 bg-amber-950/30 border border-amber-800/50 rounded text-amber-400 text-sm">
          <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
          <div>
            <span className="font-medium">Cannot start pipeline:</span> Missing {missingItems.join(', ')}
          </div>
        </div>
      )}
    </div>
  );
}
