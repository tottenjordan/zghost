import { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import type { AgentEvent } from '../../types/agents';
import type { AgentState } from '../../types/agents';
import { ChevronDown, ChevronRight, Clock, Calendar } from 'lucide-react';

interface TaskDrillDownProps {
  agentName: string;
  agentState: AgentState | undefined;
  events: AgentEvent[];
  onClose: () => void;
}

function JsonViewer({ data }: { data: any }) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="border border-zinc-700 rounded bg-zinc-950 p-2">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-1 text-xs text-zinc-400 hover:text-zinc-200"
      >
        {isExpanded ? (
          <ChevronDown className="w-3 h-3" />
        ) : (
          <ChevronRight className="w-3 h-3" />
        )}
        {isExpanded ? 'Collapse' : 'Expand'} JSON
      </button>
      {isExpanded && (
        <pre className="mt-2 text-xs overflow-x-auto text-zinc-300">
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </div>
  );
}

function formatDuration(startTime: number, endTime?: number): string {
  const duration = (endTime || Date.now()) - startTime;
  const seconds = Math.floor(duration / 1000);
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;

  if (minutes > 0) {
    return `${minutes}m ${remainingSeconds}s`;
  }
  return `${seconds}s`;
}

export function TaskDrillDown({
  agentName,
  agentState,
  events,
  onClose,
}: TaskDrillDownProps) {
  const statusVariant = {
    idle: 'default' as const,
    running: 'info' as const,
    completed: 'success' as const,
    error: 'error' as const,
  }[agentState?.status || 'idle'];

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="flex-shrink-0">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <CardTitle className="text-lg mb-2">{agentName}</CardTitle>
            <div className="flex items-center gap-2">
              <Badge variant={statusVariant}>{agentState?.status || 'idle'}</Badge>
              {agentState?.startTime && (
                <span className="text-xs text-zinc-400 flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {formatDuration(agentState.startTime, agentState.endTime)}
                </span>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-zinc-400 hover:text-zinc-200 text-sm"
          >
            Close
          </button>
        </div>
      </CardHeader>

      <CardContent className="flex-1 overflow-y-auto space-y-4">
        {/* Timing Information */}
        {agentState?.startTime && (
          <div className="space-y-2">
            <h4 className="text-sm font-semibold text-zinc-300">Timing</h4>
            <div className="space-y-1 text-xs text-zinc-400">
              <div className="flex items-center gap-2">
                <Calendar className="w-3 h-3" />
                Started: {new Date(agentState.startTime).toLocaleString()}
              </div>
              {agentState.endTime && (
                <div className="flex items-center gap-2">
                  <Calendar className="w-3 h-3" />
                  Completed: {new Date(agentState.endTime).toLocaleString()}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Error Information */}
        {agentState?.error && (
          <div className="space-y-2">
            <h4 className="text-sm font-semibold text-red-400">Error</h4>
            <div className="text-xs text-red-300 bg-red-950/50 border border-red-800 rounded p-2">
              {agentState.error}
            </div>
          </div>
        )}

        {/* Event Log */}
        <div className="space-y-2">
          <h4 className="text-sm font-semibold text-zinc-300">
            Event Log ({events.length})
          </h4>
          {events.length === 0 ? (
            <div className="text-xs text-zinc-500 italic">No events recorded</div>
          ) : (
            <div className="space-y-2">
              {events.map((event, index) => (
                <div
                  key={index}
                  className="border border-zinc-800 rounded bg-zinc-950 p-2 space-y-1"
                >
                  <div className="flex items-center gap-2 text-xs">
                    <span className="text-zinc-600">
                      {new Date(event.timestamp).toLocaleTimeString()}
                    </span>
                    <Badge
                      variant={
                        event.type === 'error'
                          ? 'error'
                          : event.type.includes('complete')
                            ? 'success'
                            : 'info'
                      }
                      className="text-xs"
                    >
                      {event.type}
                    </Badge>
                  </div>

                  {/* Tool call details */}
                  {event.type === 'tool_call' && event.data?.tool && (
                    <div className="text-xs text-zinc-300">
                      Tool: <span className="text-yellow-400">{event.data.tool}</span>
                    </div>
                  )}

                  {/* Event data */}
                  {event.data && (
                    <div className="text-xs">
                      {event.type === 'agent_step' && event.data?.content ? (
                        <div className="text-zinc-400">{event.data.content}</div>
                      ) : (
                        <JsonViewer data={event.data} />
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Session State Snapshot */}
        <div className="space-y-2">
          <h4 className="text-sm font-semibold text-zinc-300">Agent State</h4>
          {agentState ? (
            <JsonViewer data={agentState} />
          ) : (
            <div className="text-xs text-zinc-500 italic">No state available</div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
