import { useCallback, useMemo } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  ConnectionLineType,
} from 'reactflow';
import type { NodeChange, EdgeChange } from 'reactflow';
import 'reactflow/dist/style.css';
import { AgentNode } from './AgentNode';
import { PIPELINE_NODES, PIPELINE_EDGES } from './pipeline-config';
import type { OrchestrationStatus, AgentEvent, AgentStatus } from '../../types/agents';
import type { Node } from 'reactflow';

interface PipelineGraphProps {
  status: OrchestrationStatus | null;
  events: AgentEvent[];
  onSelectAgent: (agentName: string | null) => void;
}

const nodeTypes = {
  agentNode: AgentNode,
};

export function PipelineGraph({
  status,
  events,
  onSelectAgent,
}: PipelineGraphProps) {
  // Enhance nodes with runtime status
  const nodesWithStatus = useMemo(() => {
    return PIPELINE_NODES.map((node) => {
      const agentName = node.data.agentName;
      const agentEvents = events.filter((e) => e.agentName === agentName);
      const lastEvent = agentEvents[agentEvents.length - 1];
      const firstEvent = agentEvents[0];

      // Derive status from events (primary source)
      let derivedStatus: AgentStatus = 'idle';
      if (agentEvents.length > 0) {
        if (lastEvent?.type === 'agent_complete') {
          derivedStatus = 'completed';
        } else if (lastEvent?.type === 'error') {
          derivedStatus = 'error';
        } else {
          derivedStatus = 'running';
        }
      }

      // Fall back to polling status if events don't provide info
      const agentState = status?.agents[agentName];
      const finalStatus = agentEvents.length > 0
        ? derivedStatus
        : (agentState?.status || 'idle');

      let currentTool: string | undefined;
      if (lastEvent?.type === 'tool_call' && lastEvent.data?.tool) {
        currentTool = lastEvent.data.tool;
      }

      let elapsedTime: number | undefined;
      if (finalStatus === 'running' && firstEvent?.timestamp) {
        elapsedTime = Date.now() - firstEvent.timestamp;
      }

      return {
        ...node,
        data: {
          ...node.data,
          status: finalStatus,
          currentTool,
          elapsedTime,
        },
      };
    });
  }, [status, events]);

  // Enhance edges with animation for active flows
  const edgesWithAnimation = useMemo(() => {
    // Build sets of running/completed agents from events
    const runningAgents = new Set<string>();
    const completedAgents = new Set<string>();

    const agentEventMap = new Map<string, AgentEvent[]>();
    events.forEach((event) => {
      if (!agentEventMap.has(event.agentName)) {
        agentEventMap.set(event.agentName, []);
      }
      agentEventMap.get(event.agentName)!.push(event);
    });

    agentEventMap.forEach((agentEvents, agentName) => {
      const lastEvent = agentEvents[agentEvents.length - 1];
      if (lastEvent?.type === 'agent_complete') {
        completedAgents.add(agentName);
      } else if (lastEvent?.type === 'error') {
        // Errors also count as "not running"
      } else if (agentEvents.length > 0) {
        runningAgents.add(agentName);
      }
    });

    return PIPELINE_EDGES.map((edge) => {
      const isActive =
        runningAgents.has(edge.source) || runningAgents.has(edge.target);

      return {
        ...edge,
        animated: isActive,
        style: {
          stroke: isActive ? '#3b82f6' : '#52525b',
          strokeWidth: isActive ? 2 : 1,
        },
      };
    });
  }, [events]);

  // Allow drag interactions without crashing
  const onNodesChange = useCallback((_changes: NodeChange[]) => {
    // No-op: nodes are controlled via nodesWithStatus memo
  }, []);

  const onEdgesChange = useCallback((_changes: EdgeChange[]) => {
    // No-op: edges are controlled via edgesWithAnimation memo
  }, []);

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      onSelectAgent(node.data.agentName);
    },
    [onSelectAgent]
  );

  const onPaneClick = useCallback(() => {
    onSelectAgent(null);
  }, [onSelectAgent]);

  return (
    <div className="h-full w-full bg-zinc-950">
      <ReactFlow
        nodes={nodesWithStatus}
        edges={edgesWithAnimation}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        onPaneClick={onPaneClick}
        nodeTypes={nodeTypes}
        connectionLineType={ConnectionLineType.SmoothStep}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        className="bg-zinc-950"
        minZoom={0.3}
        maxZoom={1.5}
      >
        <Background color="#27272a" gap={16} />
        <Controls className="bg-zinc-800 border-zinc-700" />
        <MiniMap
          className="bg-zinc-900 border-zinc-700"
          nodeColor={(node) => {
            const nodeStatus = (node.data as any).status || 'idle';
            const colors: Record<string, string> = {
              idle: '#52525b',
              running: '#3b82f6',
              completed: '#16a34a',
              error: '#dc2626',
            };
            return colors[nodeStatus] || colors.idle;
          }}
        />
      </ReactFlow>
    </div>
  );
}
