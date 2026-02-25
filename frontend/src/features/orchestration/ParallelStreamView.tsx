import { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import type { AgentEvent } from '../../types/agents';
import { ChevronDown, ChevronRight, XCircle, CheckCircle2, Loader2 } from 'lucide-react';
import { cn } from '../../lib/utils';

interface StreamLane {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'error';
  progress: number;
  currentStage?: string;
  events: AgentEvent[];
}

interface ParallelStreamViewProps {
  streams: StreamLane[];
  onCancelStream?: (streamId: string) => void;
}

function ProgressBar({ progress }: { progress: number }) {
  return (
    <div className="w-full bg-zinc-800 rounded-full h-2 overflow-hidden">
      <div
        className="h-full bg-blue-500 transition-all duration-300"
        style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
      />
    </div>
  );
}

function StreamLaneComponent({
  stream,
  onCancel,
}: {
  stream: StreamLane;
  onCancel?: (id: string) => void;
}) {
  const [isExpanded, setIsExpanded] = useState(false);

  const statusIcon = {
    pending: Loader2,
    running: Loader2,
    completed: CheckCircle2,
    error: XCircle,
  }[stream.status];

  const StatusIcon = statusIcon;

  const statusColor = {
    pending: 'text-zinc-500',
    running: 'text-blue-400',
    completed: 'text-green-400',
    error: 'text-red-400',
  }[stream.status];

  const badgeVariant = {
    pending: 'default' as const,
    running: 'info' as const,
    completed: 'success' as const,
    error: 'error' as const,
  }[stream.status];

  return (
    <div className="border border-zinc-800 rounded bg-zinc-950 p-3 space-y-2">
      {/* Lane header */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-zinc-400 hover:text-zinc-200"
        >
          {isExpanded ? (
            <ChevronDown className="w-4 h-4" />
          ) : (
            <ChevronRight className="w-4 h-4" />
          )}
        </button>

        <StatusIcon
          className={cn(
            'w-4 h-4',
            statusColor,
            stream.status === 'running' && 'animate-spin'
          )}
        />

        <span className="font-semibold text-sm flex-1">{stream.name}</span>

        <Badge variant={badgeVariant} className="text-xs">
          {stream.status}
        </Badge>

        {stream.status === 'running' && onCancel && (
          <button
            onClick={() => onCancel(stream.id)}
            className="text-xs text-red-400 hover:text-red-300 px-2 py-1 rounded hover:bg-red-950"
          >
            Cancel
          </button>
        )}
      </div>

      {/* Progress bar */}
      <ProgressBar progress={stream.progress} />

      {/* Current stage */}
      {stream.currentStage && (
        <div className="text-xs text-zinc-400">Stage: {stream.currentStage}</div>
      )}

      {/* Event count */}
      <div className="text-xs text-zinc-500">{stream.events.length} events</div>

      {/* Expanded events */}
      {isExpanded && (
        <div className="mt-2 space-y-1 max-h-48 overflow-y-auto">
          {stream.events.length === 0 ? (
            <div className="text-xs text-zinc-600 italic">No events yet</div>
          ) : (
            stream.events.map((event, index) => (
              <div
                key={index}
                className="text-xs p-2 bg-zinc-900 rounded border border-zinc-800"
              >
                <div className="flex items-center gap-2">
                  <span className="text-zinc-600">
                    {new Date(event.timestamp).toLocaleTimeString()}
                  </span>
                  <Badge variant="default" className="text-xs">
                    {event.type}
                  </Badge>
                </div>
                {event.data && (
                  <div className="text-zinc-400 mt-1 truncate">
                    {JSON.stringify(event.data).slice(0, 100)}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

export function ParallelStreamView({ streams, onCancelStream }: ParallelStreamViewProps) {
  const completedCount = streams.filter((s) => s.status === 'completed').length;
  const totalCount = streams.length;
  const overallProgress = totalCount > 0 ? (completedCount / totalCount) * 100 : 0;

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="flex-shrink-0">
        <CardTitle className="text-base">Parallel Execution Lanes</CardTitle>
        <div className="space-y-2 mt-2">
          <div className="flex items-center justify-between text-xs text-zinc-400">
            <span>
              Overall Progress: {completedCount}/{totalCount}
            </span>
            <span>{Math.round(overallProgress)}%</span>
          </div>
          <ProgressBar progress={overallProgress} />
        </div>
      </CardHeader>

      <CardContent className="flex-1 overflow-y-auto space-y-3">
        {streams.length === 0 ? (
          <div className="text-center text-zinc-500 py-8">
            No parallel streams active
          </div>
        ) : (
          streams.map((stream) => (
            <StreamLaneComponent
              key={stream.id}
              stream={stream}
              onCancel={onCancelStream}
            />
          ))
        )}
      </CardContent>
    </Card>
  );
}
