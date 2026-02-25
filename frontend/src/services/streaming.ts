import type { AgentEvent, AgentEventType } from '../types/agents';

export function parseAgentEvent(data: any): AgentEvent {
  return {
    type: data.type as AgentEventType,
    agentName: data.agent_name || data.agentName || 'unknown',
    data: data.data || data,
    timestamp: data.timestamp || Date.now(),
  };
}

export function createEventStream(
  url: string,
  onEvent: (event: AgentEvent) => void,
  onError?: (error: Event) => void
): () => void {
  const source = new EventSource(url);

  source.onmessage = (e) => {
    try {
      const parsed = JSON.parse(e.data);
      onEvent(parseAgentEvent(parsed));
    } catch (error) {
      console.error('Failed to parse SSE event:', error);
    }
  };

  source.onerror = (error) => {
    console.error('SSE connection error:', error);
    if (onError) {
      onError(error);
    }
  };

  return () => source.close();
}
