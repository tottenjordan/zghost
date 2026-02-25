import type { AgentEvent } from '../../types/agents';

/**
 * Mock EventSource for testing SSE streaming
 */
export class MockEventSource extends EventTarget {
  url: string;
  onmessage: ((e: MessageEvent) => void) | null = null;
  onerror: ((e: Event) => void) | null = null;
  readyState = 1; // OPEN

  constructor(url: string) {
    super();
    this.url = url;
  }

  close() {
    this.readyState = 2; // CLOSED
  }

  // Helper method to simulate receiving an event
  simulateMessage(data: any) {
    const event = new MessageEvent('message', {
      data: JSON.stringify(data),
    });
    if (this.onmessage) {
      this.onmessage(event);
    }
  }

  // Helper method to simulate an error
  simulateError() {
    const event = new Event('error');
    if (this.onerror) {
      this.onerror(event);
    }
  }
}

/**
 * Create a sequence of mock agent events for testing
 */
export function createMockEventSequence(): AgentEvent[] {
  const now = Date.now();
  return [
    {
      type: 'agent_start',
      agentName: 'test_agent',
      data: { message: 'Agent started' },
      timestamp: now,
    },
    {
      type: 'tool_call',
      agentName: 'test_agent',
      data: { tool: 'test_tool', args: { param: 'value' } },
      timestamp: now + 1000,
    },
    {
      type: 'tool_response',
      agentName: 'test_agent',
      data: { result: 'Tool executed successfully' },
      timestamp: now + 2000,
    },
    {
      type: 'agent_complete',
      agentName: 'test_agent',
      data: { status: 'success' },
      timestamp: now + 3000,
    },
  ];
}

/**
 * Create a mock error event sequence
 */
export function createMockErrorSequence(): AgentEvent[] {
  const now = Date.now();
  return [
    {
      type: 'agent_start',
      agentName: 'test_agent',
      data: { message: 'Agent started' },
      timestamp: now,
    },
    {
      type: 'error',
      agentName: 'test_agent',
      data: { error: 'Something went wrong' },
      timestamp: now + 1000,
    },
  ];
}
