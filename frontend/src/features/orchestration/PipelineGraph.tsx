import { useCallback, useMemo, useState, useEffect } from 'react';
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

/** Set of agent names known in the pipeline config */
const KNOWN_AGENT_NAMES = new Set(PIPELINE_NODES.map((n) => n.data.agentName));

/** Infer sub-agent activity from tool_call / tool_response events */
function inferSubAgentStatus(events: AgentEvent[]): Map<string, { status: AgentStatus; start: number; end?: number }> {
  const inferred = new Map<string, { status: AgentStatus; start: number; end?: number }>();

  for (const event of events) {
    const parts = event.data?.parts;
    if (!parts || !Array.isArray(parts)) continue;

    for (const part of parts) {
      if (part.function_call?.name && KNOWN_AGENT_NAMES.has(part.function_call.name)) {
        const name = part.function_call.name;
        if (!inferred.has(name)) {
          inferred.set(name, { status: 'running', start: event.timestamp });
        }
      }
      if (part.function_response?.name && KNOWN_AGENT_NAMES.has(part.function_response.name)) {
        const name = part.function_response.name;
        const entry = inferred.get(name);
        if (entry) {
          entry.status = 'completed';
          entry.end = event.timestamp;
        } else {
          inferred.set(name, { status: 'completed', start: event.timestamp, end: event.timestamp });
        }
      }
    }
  }

  return inferred;
}

interface PipelineGraphProps {
  status: OrchestrationStatus | null;
  events: AgentEvent[];
  onSelectAgent: (agentName: string | null) => void;
}

const nodeTypes = {
  agentNode: AgentNode,
};

const PHASE_MAP: Record<string, { name: string; estimatedMin: number }> = {
  'trends_and_insights_agent': { name: 'Trend Discovery', estimatedMin: 1 },
  'research_orchestrator': { name: 'Market Research', estimatedMin: 3 },
  'combined_research_pipeline': { name: 'Market Research', estimatedMin: 3 },
  'ad_content_generator_agent': { name: 'Ad Creative', estimatedMin: 3 },
  'ad_copy_drafter': { name: 'Drafting Ad Copy', estimatedMin: 1 },
  'ad_copy_critic': { name: 'Critiquing Ad Copy', estimatedMin: 1 },
  'visual_concept_drafter': { name: 'Drafting Visual Concepts', estimatedMin: 1 },
  'visual_concept_critic': { name: 'Critiquing Visual Concepts', estimatedMin: 0.5 },
  'visual_concept_finalizer': { name: 'Finalizing Visual Concepts', estimatedMin: 0.5 },
  'visual_generator': { name: 'Generating Visuals', estimatedMin: 5 },
  'av_editing_studio_agent': { name: 'AV Studio Production', estimatedMin: 5 },
  'focus_group_evaluator_agent': { name: 'Focus Group Evaluation', estimatedMin: 2 },
};

function PhaseIndicator({ events }: { events: AgentEvent[] }) {
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    const interval = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(interval);
  }, []);

  const phase = useMemo(() => {
    const agentLastEvent = new Map<string, AgentEvent>();
    for (const event of events) {
      agentLastEvent.set(event.agentName, event);
    }
    let latestRunning: { name: string; startTime: number; estimated: number } | null = null;
    for (const [agentName, lastEvent] of agentLastEvent) {
      if (lastEvent.type !== 'agent_complete' && lastEvent.type !== 'error') {
        const p = PHASE_MAP[agentName];
        if (p) {
          const agentEvents = events.filter(e => e.agentName === agentName);
          const startTime = agentEvents[0]?.timestamp || now;
          if (!latestRunning || startTime > latestRunning.startTime) {
            latestRunning = { name: p.name, startTime, estimated: p.estimatedMin };
          }
        }
      }
    }
    if (!latestRunning) return null;
    return {
      name: latestRunning.name,
      elapsed: now - latestRunning.startTime,
      estimated: latestRunning.estimated,
    };
  }, [events, now]);

  if (!phase) return null;

  const elapsedSec = Math.floor(phase.elapsed / 1000);
  const min = Math.floor(elapsedSec / 60);
  const sec = elapsedSec % 60;
  const timeStr = `${min}:${sec.toString().padStart(2, '0')}`;
  const estStr = phase.estimated > 0 ? ` / ~${phase.estimated}m` : '';

  return (
    <div className="absolute top-3 left-3 z-10 flex items-center gap-2 rounded-lg bg-zinc-900/90 border border-zinc-700 px-3 py-1.5 shadow-lg backdrop-blur-sm">
      <span className="relative flex h-2 w-2">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75" />
        <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500" />
      </span>
      <span className="text-sm font-medium text-zinc-200">{phase.name}</span>
      <span className="text-xs text-zinc-400">{timeStr}{estStr}</span>
    </div>
  );
}

export function PipelineGraph({
  status,
  events,
  onSelectAgent,
}: PipelineGraphProps) {
  // Enhance nodes with runtime status
  const nodesWithStatus = useMemo(() => {
    const inferredStatus = inferSubAgentStatus(events);

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
      } else if (inferredStatus.has(agentName)) {
        // No direct events, but inferred from tool_call/tool_response
        derivedStatus = inferredStatus.get(agentName)!.status;
      }

      // Fall back to polling status if events don't provide info
      const agentState = status?.agents[agentName];
      const finalStatus = (agentEvents.length > 0 || inferredStatus.has(agentName))
        ? derivedStatus
        : (agentState?.status || 'idle');

      let currentTool: string | undefined;
      if (lastEvent?.type === 'tool_call' && lastEvent.data?.tool) {
        currentTool = lastEvent.data.tool;
      }

      let elapsedTime: number | undefined;
      const effectiveStart = firstEvent?.timestamp || inferredStatus.get(agentName)?.start;
      if (finalStatus === 'running' && effectiveStart) {
        elapsedTime = Date.now() - effectiveStart;
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
    // Build sets of running/completed agents from events + inference
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

    // Also include inferred sub-agent status
    const inferredStatus = inferSubAgentStatus(events);
    inferredStatus.forEach((info, agentName) => {
      if (info.status === 'running') runningAgents.add(agentName);
      if (info.status === 'completed') completedAgents.add(agentName);
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
      <PhaseIndicator events={events} />
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
