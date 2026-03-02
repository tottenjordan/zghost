import { useEffect, useRef, useState } from 'react';
import { Badge } from '../../components/ui/Badge';
import type { AgentEvent, AgentEventType } from '../../types/agents';
import {
  PlayCircle,
  Zap,
  CheckCircle2,
  MessageSquare,
  XCircle,
  Search,
  Filter,
  Pause,
  Play,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { cn } from '../../lib/utils';

interface EventStreamProps {
  events: AgentEvent[];
  isPaused: boolean;
  onTogglePause: () => void;
  onFilterAgent: (agentName: string) => void;
  onFilterEventType: (eventType: AgentEventType) => void;
  onSearch: (term: string) => void;
}

const eventTypeIcons: Record<AgentEventType, any> = {
  agent_start: PlayCircle,
  tool_call: Zap,
  tool_response: CheckCircle2,
  tool_start: Zap,
  tool_end: CheckCircle2,
  agent_step: MessageSquare,
  agent_complete: CheckCircle2,
  error: XCircle,
};

const eventTypeColors: Record<AgentEventType, string> = {
  agent_start: 'text-blue-400',
  tool_call: 'text-yellow-400',
  tool_response: 'text-green-400',
  tool_start: 'text-yellow-400',
  tool_end: 'text-green-400',
  agent_step: 'text-zinc-300',
  agent_complete: 'text-green-500',
  error: 'text-red-400',
};

function formatTimestamp(timestamp: number): string {
  const date = new Date(timestamp);
  return date.toLocaleTimeString('en-US', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    fractionalSecondDigits: 3,
  });
}

function formatEventSummary(event: AgentEvent): string {
  if (event.type === 'tool_call' && event.data?.tool) {
    return `Tool: ${event.data.tool}`;
  }
  if (event.type === 'tool_response' && event.data?.result) {
    const result = JSON.stringify(event.data.result);
    return result.length > 120 ? `${result.slice(0, 120)}...` : result;
  }
  if (event.type === 'error' && event.data?.message) {
    return event.data.message;
  }
  if (event.type === 'agent_step' && event.data?.content) {
    const content = event.data.content;
    return content.length > 120 ? `${content.slice(0, 120)}...` : content;
  }
  const raw = JSON.stringify(event.data);
  return raw.length > 120 ? `${raw.slice(0, 120)}...` : raw;
}

function formatEventFull(event: AgentEvent): string {
  if (event.type === 'tool_call' && event.data?.tool) {
    const args = event.data.args ? JSON.stringify(event.data.args, null, 2) : '';
    return `Tool: ${event.data.tool}${args ? `\n\nArguments:\n${args}` : ''}`;
  }
  if (event.type === 'tool_response' && event.data?.result) {
    return typeof event.data.result === 'string'
      ? event.data.result
      : JSON.stringify(event.data.result, null, 2);
  }
  if (event.type === 'error' && event.data?.message) {
    return event.data.message;
  }
  if (event.type === 'agent_step' && event.data?.content) {
    return event.data.content;
  }
  return JSON.stringify(event.data, null, 2);
}

function hasMoreContent(event: AgentEvent): boolean {
  const summary = formatEventSummary(event);
  return summary.endsWith('...');
}

export function EventStream({
  events,
  isPaused,
  onTogglePause,
  onFilterAgent,
  onFilterEventType,
  onSearch,
}: EventStreamProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [expandedEvents, setExpandedEvents] = useState<Set<number>>(new Set());

  const toggleExpanded = (index: number) => {
    setExpandedEvents((prev) => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  };

  // Auto-scroll to bottom when new events arrive (if not paused)
  useEffect(() => {
    if (!isPaused && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events, isPaused]);

  const handleSearch = (value: string) => {
    setSearchTerm(value);
    onSearch(value);
  };

  return (
    <div className="flex flex-col h-full bg-zinc-900 border border-zinc-800 rounded-lg">
      {/* Header with controls */}
      <div className="flex items-center gap-2 p-3 border-b border-zinc-800">
        <h3 className="font-semibold text-sm flex-1">Event Stream</h3>
        <div className="flex items-center gap-2">
          {/* Collapse/Expand */}
          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="p-2 rounded hover:bg-zinc-800 transition-colors"
            title={isCollapsed ? 'Expand event stream' : 'Collapse event stream'}
          >
            {isCollapsed ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </button>
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
            <input
              type="text"
              placeholder="Search..."
              value={searchTerm}
              onChange={(e) => handleSearch(e.target.value)}
              className="pl-8 pr-3 py-1 text-sm bg-zinc-800 border border-zinc-700 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Filter toggle */}
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={cn(
              'p-2 rounded hover:bg-zinc-800 transition-colors',
              showFilters && 'bg-zinc-800'
            )}
          >
            <Filter className="w-4 h-4" />
          </button>

          {/* Pause/Resume */}
          <button
            onClick={onTogglePause}
            className="p-2 rounded hover:bg-zinc-800 transition-colors"
            title={isPaused ? 'Resume auto-scroll' : 'Pause auto-scroll'}
          >
            {isPaused ? (
              <Play className="w-4 h-4 text-blue-400" />
            ) : (
              <Pause className="w-4 h-4" />
            )}
          </button>

          {/* Event count */}
          <Badge variant="default" className="text-xs">
            {events.length}
          </Badge>
        </div>
      </div>

      {/* Filters (collapsible) */}
      {!isCollapsed && showFilters && (
        <div className="p-3 border-b border-zinc-800 bg-zinc-950/50 space-y-2">
          <div className="text-xs text-zinc-400">Click on event badges to filter</div>
        </div>
      )}

      {/* Event list */}
      {!isCollapsed && (
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto p-3 space-y-2 font-mono text-xs"
        >
        {events.length === 0 ? (
          <div className="text-center text-zinc-500 py-8">
            No events yet. Start the pipeline to see activity.
          </div>
        ) : (
          events.map((event, index) => {
            const Icon = eventTypeIcons[event.type] || MessageSquare;
            const color = eventTypeColors[event.type] || 'text-zinc-400';
            const isExpanded = expandedEvents.has(index);
            const expandable = hasMoreContent(event);

            return (
              <div
                key={index}
                className={cn(
                  'rounded bg-zinc-950/50 hover:bg-zinc-800/50 transition-colors',
                  expandable && 'cursor-pointer',
                )}
                onClick={() => expandable && toggleExpanded(index)}
              >
                <div className="flex items-start gap-2 p-2">
                  {/* Timestamp */}
                  <span className="text-zinc-600 flex-shrink-0">
                    {formatTimestamp(event.timestamp)}
                  </span>

                  {/* Agent badge */}
                  <button
                    onClick={(e) => { e.stopPropagation(); onFilterAgent(event.agentName); }}
                    className="flex-shrink-0"
                  >
                    <Badge variant="default" className="text-xs cursor-pointer hover:bg-zinc-600">
                      {event.agentName}
                    </Badge>
                  </button>

                  {/* Event type icon and badge */}
                  <button
                    onClick={(e) => { e.stopPropagation(); onFilterEventType(event.type); }}
                    className="flex items-center gap-1 flex-shrink-0 cursor-pointer"
                  >
                    <Icon className={cn('w-3 h-3', color)} />
                    <span className={cn('text-xs', color)}>{event.type}</span>
                  </button>

                  {/* Event data preview */}
                  {!isExpanded && (
                    <span className="text-zinc-400 flex-1 truncate">
                      {formatEventSummary(event)}
                    </span>
                  )}

                  {/* Expand indicator */}
                  {expandable && (
                    <button
                      onClick={(e) => { e.stopPropagation(); toggleExpanded(index); }}
                      className="flex-shrink-0 p-0.5 rounded hover:bg-zinc-700 transition-colors"
                    >
                      {isExpanded ? (
                        <ChevronUp className="w-3 h-3 text-zinc-500" />
                      ) : (
                        <ChevronDown className="w-3 h-3 text-zinc-500" />
                      )}
                    </button>
                  )}
                </div>

                {/* Expanded content */}
                {isExpanded && (
                  <div className="px-2 pb-2 pt-0">
                    <pre className="text-zinc-300 text-[11px] leading-relaxed whitespace-pre-wrap break-words bg-zinc-900/80 rounded p-2 border border-zinc-800 max-h-64 overflow-y-auto">
                      {formatEventFull(event)}
                    </pre>
                  </div>
                )}
              </div>
            );
          })
        )}
        </div>
      )}
    </div>
  );
}
