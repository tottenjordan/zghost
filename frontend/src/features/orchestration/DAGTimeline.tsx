import { useMemo, useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { cn } from '../../lib/utils';
import { PIPELINE_NODES } from './pipeline-config';
import type { AgentEvent } from '../../types/agents';

export interface TimelineTask {
  id: string;
  agentName: string;
  label: string;
  skill: 'root' | 'trends' | 'research' | 'creative' | 'av';
  status: 'pending' | 'running' | 'completed' | 'error';
  startTime?: number;
  endTime?: number;
  eventCount: number;
}

interface DAGTimelineProps {
  events: AgentEvent[];
  pipelineStartTime?: number;
  onSelectAgent: (agentName: string | null) => void;
  selectedAgent: string | null;
}

const SKILL_META: Record<string, { label: string; color: string; bgColor: string; borderColor: string }> = {
  root: { label: 'Orchestrator', color: 'text-zinc-300', bgColor: 'bg-zinc-900/50', borderColor: 'border-zinc-700/50' },
  trends: { label: 'Trend Discovery', color: 'text-emerald-400', bgColor: 'bg-emerald-950/20', borderColor: 'border-emerald-800/40' },
  research: { label: 'Market Research', color: 'text-blue-400', bgColor: 'bg-blue-950/20', borderColor: 'border-blue-800/40' },
  creative: { label: 'Ad Creative', color: 'text-purple-400', bgColor: 'bg-purple-950/20', borderColor: 'border-purple-800/40' },
  av: { label: 'AV Studio', color: 'text-amber-400', bgColor: 'bg-amber-950/20', borderColor: 'border-amber-800/40' },
};

function formatElapsed(ms: number): string {
  const seconds = Math.floor(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}m ${remainingSeconds}s`;
}

/** Convert raw events into timeline tasks */
function buildTimelineTasks(events: AgentEvent[]): TimelineTask[] {
  const agentEvents = new Map<string, AgentEvent[]>();
  events.forEach((event) => {
    const list = agentEvents.get(event.agentName) || [];
    list.push(event);
    agentEvents.set(event.agentName, list);
  });

  return PIPELINE_NODES.map((node) => {
    const agentName = node.data.agentName;
    const nodeEvents = agentEvents.get(agentName) || [];
    const skill = (node.data.skill || 'root') as TimelineTask['skill'];

    let status: TimelineTask['status'] = 'pending';
    let startTime: number | undefined;
    let endTime: number | undefined;

    if (nodeEvents.length > 0) {
      startTime = nodeEvents[0].timestamp;
      const lastEvent = nodeEvents[nodeEvents.length - 1];

      if (lastEvent.type === 'agent_complete') {
        status = 'completed';
        endTime = lastEvent.timestamp;
      } else if (lastEvent.type === 'error') {
        status = 'error';
        endTime = lastEvent.timestamp;
      } else {
        status = 'running';
      }
    }

    return {
      id: node.id,
      agentName,
      label: node.data.label,
      skill,
      status,
      startTime,
      endTime,
      eventCount: nodeEvents.length,
    };
  });
}

export function DAGTimeline({ events, pipelineStartTime, onSelectAgent, selectedAgent }: DAGTimelineProps) {
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());

  const tasks = useMemo(() => buildTimelineTasks(events), [events]);

  const now = Date.now();
  const startTime = pipelineStartTime || tasks.reduce((min, t) => {
    if (t.startTime && t.startTime < min) return t.startTime;
    return min;
  }, now);

  const endTime = tasks.reduce((max, t) => {
    const end = t.endTime || (t.status === 'running' ? now : t.startTime || 0);
    return end > max ? end : max;
  }, startTime);

  const totalDuration = Math.max(endTime - startTime, 1000);

  // Group tasks by skill
  const groups = useMemo(() => {
    const skillOrder = ['root', 'trends', 'research', 'creative', 'av'];
    return skillOrder
      .map((skill) => ({
        skill,
        ...SKILL_META[skill],
        tasks: tasks.filter((t) => t.skill === skill),
      }))
      .filter((g) => g.tasks.length > 0);
  }, [tasks]);

  const toggleGroup = (skill: string) => {
    setCollapsedGroups((prev) => {
      const next = new Set(prev);
      next.has(skill) ? next.delete(skill) : next.add(skill);
      return next;
    });
  };

  // Time markers
  const markerInterval = totalDuration > 120000 ? 30000 : totalDuration > 30000 ? 10000 : 5000;
  const markers: number[] = [];
  for (let t = 0; t <= totalDuration; t += markerInterval) {
    markers.push(t);
  }

  const completed = tasks.filter((t) => t.status === 'completed').length;
  const running = tasks.filter((t) => t.status === 'running').length;
  const errored = tasks.filter((t) => t.status === 'error').length;
  const pending = tasks.filter((t) => t.status === 'pending').length;
  const hasData = events.length > 0;

  if (!hasData) {
    return (
      <div className="flex h-72 items-center justify-center rounded-lg border border-zinc-800 bg-zinc-900/50 text-zinc-500">
        <div className="text-center">
          <p className="text-sm font-medium">No timeline data yet</p>
          <p className="mt-1 text-xs">Start the pipeline to see agent execution</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {/* Summary */}
      <div className="flex items-center gap-3 text-xs text-zinc-500">
        <span>{tasks.length} agents</span>
        <span className="h-3 w-px bg-zinc-700" />
        {completed > 0 && <span className="text-green-400">{completed} done</span>}
        {running > 0 && <span className="text-blue-400">{running} running</span>}
        {errored > 0 && <span className="text-red-400">{errored} error</span>}
        {pending > 0 && <span>{pending} pending</span>}
        <span className="ml-auto font-mono">{formatElapsed(totalDuration)}</span>
      </div>

      {/* Time axis */}
      <div className="relative ml-44 h-4 border-b border-zinc-800">
        {markers.map((t) => (
          <div
            key={t}
            className="absolute top-0 flex flex-col items-center"
            style={{ left: `${(t / totalDuration) * 100}%` }}
          >
            <div className="h-2 w-px bg-zinc-700" />
            <span className="mt-px text-[9px] text-zinc-600">{formatElapsed(t)}</span>
          </div>
        ))}
      </div>

      {/* Groups */}
      <div className="space-y-1">
        {groups.map((group) => {
          const isCollapsed = collapsedGroups.has(group.skill);
          const groupDone = group.tasks.filter((t) => t.status === 'completed').length;
          const groupRunning = group.tasks.filter((t) => t.status === 'running').length;

          return (
            <div key={group.skill} className={cn('rounded-lg border', group.borderColor, group.bgColor)}>
              <button
                onClick={() => toggleGroup(group.skill)}
                className="flex w-full items-center gap-2 px-3 py-1.5"
              >
                {isCollapsed ? (
                  <ChevronRight className="h-3 w-3 text-zinc-500" />
                ) : (
                  <ChevronDown className="h-3 w-3 text-zinc-500" />
                )}
                <span className={cn('text-xs font-semibold', group.color)}>{group.label}</span>
                <span className="text-[10px] text-zinc-600">
                  {groupDone}/{group.tasks.length}
                  {groupRunning > 0 && <span className="ml-1 text-blue-400">({groupRunning} active)</span>}
                </span>
              </button>

              {!isCollapsed && (
                <div className="space-y-px pb-1">
                  {group.tasks.map((task) => {
                    const barLeft = task.startTime
                      ? ((task.startTime - startTime) / totalDuration) * 100
                      : 0;
                    const barEnd = task.endTime
                      ? task.endTime
                      : task.status === 'running' ? now : task.startTime || startTime;
                    const barWidth = task.startTime
                      ? Math.max(((barEnd - task.startTime) / totalDuration) * 100, 0.5)
                      : 0;
                    const isSelected = selectedAgent === task.agentName;
                    const duration = task.startTime ? formatElapsed(barEnd - task.startTime) : '';

                    return (
                      <button
                        key={task.id}
                        onClick={() => onSelectAgent(task.agentName)}
                        className={cn(
                          'group flex w-full items-center px-3 py-1 text-left transition-colors hover:bg-zinc-800/30',
                          isSelected && 'bg-zinc-800/50 ring-1 ring-inset ring-blue-500/40'
                        )}
                      >
                        {/* Label */}
                        <div className="w-40 flex-shrink-0 pr-2">
                          <span className="truncate text-xs text-zinc-300 group-hover:text-zinc-100">
                            {task.label}
                          </span>
                        </div>

                        {/* Bar */}
                        <div className="relative flex-1 h-5">
                          {task.startTime ? (
                            <div
                              className={cn(
                                'absolute top-0.5 h-4 rounded-md',
                                task.status === 'pending' && 'bg-zinc-700/50',
                                task.status === 'running' && 'bg-blue-500 animate-pulse',
                                task.status === 'completed' && 'bg-green-600',
                                task.status === 'error' && 'bg-red-500',
                              )}
                              style={{ left: `${barLeft}%`, width: `${barWidth}%` }}
                            >
                              {barWidth > 8 && (
                                <span className="absolute inset-0 flex items-center justify-center text-[10px] font-medium text-white/80">
                                  {duration}
                                </span>
                              )}
                            </div>
                          ) : (
                            <div className="absolute top-0.5 left-0 right-0 h-4 rounded-md border border-dashed border-zinc-700/40 bg-zinc-800/20" />
                          )}
                        </div>

                        {/* Status */}
                        <div className="w-12 flex-shrink-0 text-right">
                          <span className={cn(
                            'text-[10px] font-medium',
                            task.status === 'completed' && 'text-green-400',
                            task.status === 'running' && 'text-blue-400',
                            task.status === 'error' && 'text-red-400',
                            task.status === 'pending' && 'text-zinc-600',
                          )}>
                            {task.status === 'completed' ? 'Done' :
                             task.status === 'running' ? 'Active' :
                             task.status === 'error' ? 'Error' : ''}
                          </span>
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
