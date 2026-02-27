import type { AgentEvent, AgentEventType } from '../types/agents';

export function parseAgentEvent(data: any): AgentEvent {
  // Ensure timestamp is epoch ms (server may send ISO string or epoch ms)
  let ts = data.timestamp;
  if (typeof ts === 'string') {
    ts = new Date(ts).getTime();
  }
  if (typeof ts !== 'number' || isNaN(ts)) {
    ts = Date.now();
  }

  return {
    type: data.type as AgentEventType,
    agentName: data.agent_name || data.agentName || 'unknown',
    data: data.data || data,
    timestamp: ts,
  };
}

export function createEventStream(
  url: string,
  onEvent: (event: AgentEvent) => void,
  onError?: (error: Event) => void,
  onComplete?: () => void
): () => void {
  const source = new EventSource(url);

  source.onmessage = (e) => {
    try {
      const parsed = JSON.parse(e.data);
      const event = parseAgentEvent(parsed);
      onEvent(event);

      // Auto-close when stream completes to prevent reconnect loops
      if (parsed.type === 'agent_complete' && parsed.session_id) {
        source.close();
        onComplete?.();
      }
    } catch (error) {
      console.error('Failed to parse SSE event:', error);
    }
  };

  source.onerror = (error) => {
    // EventSource fires onerror when the connection closes normally after
    // the server finishes streaming. Only log if it's a real error.
    if (source.readyState === EventSource.CLOSED) {
      onComplete?.();
      return;
    }
    console.error('SSE connection error:', error);
    if (onError) {
      onError(error);
    }
  };

  return () => source.close();
}
