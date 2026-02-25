import { memo } from 'react';
import { Handle, Position } from 'reactflow';
import type { NodeProps } from 'reactflow';
import { Badge } from '../../components/ui/Badge';
import type { PipelineNodeData } from './pipeline-config';
import type { AgentStatus } from '../../types/agents';
import { cn } from '../../lib/utils';
import {
  Workflow,
  GitBranch,
  Wrench,
  Activity,
  CheckCircle2,
  XCircle,
  Clock,
} from 'lucide-react';

interface AgentNodeProps extends NodeProps {
  data: PipelineNodeData & {
    status?: AgentStatus;
    currentTool?: string;
    elapsedTime?: number;
  };
}

const typeIcons = {
  orchestrator: Workflow,
  sequential: Activity,
  parallel: GitBranch,
  tool: Wrench,
};

const statusColors = {
  idle: 'bg-zinc-700 border-zinc-600',
  running: 'bg-blue-900/50 border-blue-500 shadow-blue-500/50 shadow-lg',
  completed: 'bg-green-900/50 border-green-500',
  error: 'bg-red-900/50 border-red-500',
};

const statusBadgeVariants = {
  idle: 'default' as const,
  running: 'info' as const,
  completed: 'success' as const,
  error: 'error' as const,
};

function AgentNodeComponent({ data, selected }: AgentNodeProps) {
  const status = data.status || 'idle';
  const Icon = typeIcons[data.type];
  const isActive = status === 'running';

  const StatusIcon = {
    idle: Clock,
    running: Activity,
    completed: CheckCircle2,
    error: XCircle,
  }[status];

  return (
    <>
      <Handle type="target" position={Position.Top} className="w-2 h-2" />
      <div
        className={cn(
          'rounded-lg border-2 bg-zinc-900 p-3 min-w-[180px] transition-all',
          statusColors[status],
          selected && 'ring-2 ring-blue-400',
          isActive && 'animate-pulse'
        )}
      >
        <div className="flex items-start gap-2">
          <Icon className="w-4 h-4 mt-0.5 text-zinc-400 flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <div className="font-semibold text-sm text-zinc-100 mb-1 truncate">
              {data.label}
            </div>
            <div className="flex items-center gap-2 mb-1">
              <Badge variant={statusBadgeVariants[status]} className="text-xs">
                <StatusIcon className="w-3 h-3 mr-1" />
                {status}
              </Badge>
            </div>
            {data.description && (
              <div className="text-xs text-zinc-400 mb-1 truncate">
                {data.description}
              </div>
            )}
            {data.currentTool && (
              <div className="text-xs text-blue-400 truncate">
                <Wrench className="w-3 h-3 inline mr-1" />
                {data.currentTool}
              </div>
            )}
            {data.elapsedTime !== undefined && status === 'running' && (
              <div className="text-xs text-zinc-500 mt-1">
                {Math.floor(data.elapsedTime / 1000)}s
              </div>
            )}
          </div>
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} className="w-2 h-2" />
    </>
  );
}

export const AgentNode = memo(AgentNodeComponent);
