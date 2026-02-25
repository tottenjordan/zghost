export type AgentStatus = 'idle' | 'running' | 'completed' | 'error';

export interface AgentState {
  name: string;
  status: AgentStatus;
  startTime?: number;
  endTime?: number;
  error?: string;
}

export interface OrchestrationStatus {
  overall_status: AgentStatus;
  agents: Record<string, AgentState>;
  started_at?: string;
  completed_at?: string;
}

export interface DispatchConfig {
  session_id: string;
  agents: string[];
  parallel?: boolean;
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
