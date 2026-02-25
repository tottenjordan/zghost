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
import type { OrchestrationStatus, AgentEvent } from '../../types/agents';
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
      const agentState = status?.agents[agentName];
      const agentEvents = events.filter((e) => e.agentName === agentName);
      const lastEvent = agentEvents[agentEvents.length - 1];

      let currentTool: string | undefined;
      if (lastEvent?.type === 'tool_call' && lastEvent.data?.tool) {
        currentTool = lastEvent.data.tool;
      }

      let elapsedTime: number | undefined;
      if (agentState?.status === 'running' && agentState.startTime) {
        elapsedTime = Date.now() - agentState.startTime;
      }

      return {
        ...node,
        data: {
          ...node.data,
          status: agentState?.status || 'idle',
          currentTool,
          elapsedTime,
        },
      };
    });
  }, [status, events]);

  // Enhance edges with animation for active flows
  const edgesWithAnimation = useMemo(() => {
    return PIPELINE_EDGES.map((edge) => {
      const sourceAgent = status?.agents[edge.source];
      const targetAgent = status?.agents[edge.target];
      const isActive =
        sourceAgent?.status === 'running' || targetAgent?.status === 'running';

      return {
        ...edge,
        animated: isActive,
        style: {
          stroke: isActive ? '#3b82f6' : '#52525b',
          strokeWidth: isActive ? 2 : 1,
        },
      };
    });
  }, [status]);

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
