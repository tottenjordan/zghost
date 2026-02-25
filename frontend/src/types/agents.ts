export type AgentStatus = 'idle' | 'running' | 'completed' | 'error';

export interface AgentState {
  name?: string;
  status: AgentStatus;
  startTime?: number;
  endTime?: number;
  lastUpdate?: string;
  error?: string;
}

export interface OrchestrationStatus {
  sessionId: string;
  pipelineStatus: AgentStatus;
  agents: Record<string, AgentState>;
  startedAt?: string;
  completedAt?: string;
}

export type AgentEventType =
  | 'agent_start'
  | 'agent_step'
  | 'tool_call'
  | 'tool_response'
  | 'tool_start'
  | 'tool_end'
  | 'agent_complete'
  | 'error';

export interface AgentEvent {
  type: AgentEventType;
  agentName: string;
  data: any;
  timestamp: number;
}
