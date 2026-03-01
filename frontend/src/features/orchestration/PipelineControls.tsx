import { useState, useEffect } from 'react';
import { Badge } from '../../components/ui/Badge';
import { Play, Square, RefreshCw, Activity, AlertTriangle, Check } from 'lucide-react';
import { cn } from '../../lib/utils';

interface PipelineControlsProps {
  isRunning: boolean;
  sessionId: string | null;
  readyToLaunch: boolean;
  missingItems: string[];
  commercialDuration: 10 | 15 | 20 | 30;
  autopilot: boolean;
  onDurationChange: (duration: 10 | 15 | 20 | 30) => void;
  onAutopilotChange: (autopilot: boolean) => void;
  onStart: () => void;
  onStop: () => void;
  onRefresh: () => void;
}

export function PipelineControls({
  isRunning,
  sessionId,
  readyToLaunch,
  missingItems,
  commercialDuration,
  autopilot,
  onDurationChange,
  onAutopilotChange,
  onStart,
  onStop,
  onRefresh,
}: PipelineControlsProps) {
  const [durationChanged, setDurationChanged] = useState(false);

  // Clear duration change indicator after 2 seconds
  useEffect(() => {
    if (durationChanged) {
      const timer = setTimeout(() => setDurationChanged(false), 2000);
      return () => clearTimeout(timer);
    }
  }, [durationChanged]);

  const handleDurationChange = (duration: 10 | 15 | 20 | 30) => {
    onDurationChange(duration);
    setDurationChanged(true);
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-4 p-4 bg-zinc-900 border border-zinc-800 rounded-lg">
        {/* Active session indicator */}
        <div className="flex items-center gap-2 flex-1">
          <Activity className={cn('w-4 h-4', isRunning && 'text-green-400 animate-pulse')} />
          <span className="text-sm text-zinc-400">Active Session:</span>
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

        {/* Duration selector */}
        <div className="flex items-center gap-2">
          <label htmlFor="duration" className="text-sm text-zinc-400">
            Duration:
          </label>
          <select
            id="duration"
            value={commercialDuration}
            onChange={(e) => handleDurationChange(Number(e.target.value) as 10 | 15 | 20 | 30)}
            disabled={isRunning}
            className={cn(
              "px-3 py-1 text-sm bg-zinc-800 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors",
              durationChanged ? "border-green-500" : "border-zinc-700"
            )}
          >
            <option value={10}>10s</option>
            <option value={15}>15s</option>
            <option value={20}>20s</option>
            <option value={30}>30s</option>
          </select>
          {durationChanged && (
            <Check className="w-4 h-4 text-green-400 animate-in fade-in" />
          )}
        </div>

        {/* Autopilot toggle — always clickable */}
        <div
          className="flex items-center gap-2 pl-2 border-l border-zinc-700 cursor-pointer"
          onClick={() => onAutopilotChange(!autopilot)}
        >
          <button
            className={cn(
              'relative inline-flex h-6 w-11 items-center rounded-full transition-colors pointer-events-none',
              autopilot ? 'bg-blue-600' : 'bg-zinc-700'
            )}
            title={autopilot ? 'Autopilot ON — auto-approves all agent outputs' : 'Autopilot OFF — manual approval required'}
          >
            <span className={cn(
              'inline-block h-4 w-4 transform rounded-full bg-white transition-transform',
              autopilot ? 'translate-x-6' : 'translate-x-1'
            )} />
          </button>
          <span className={cn(
            'text-xs font-medium',
            autopilot ? 'text-blue-400' : 'text-zinc-500'
          )}>
            {autopilot ? 'Autopilot' : 'Manual'}
          </span>
        </div>

        {/* Control buttons */}
        <div className="flex items-center gap-2">
          {!isRunning ? (
            <button
              onClick={onStart}
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
