import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '../test-utils';
import { AgentChat } from '../../features/orchestration/AgentChat';
import type { AgentEvent } from '../../types/agents';

// Mock the api module
vi.mock('../../services/api', () => ({
  api: {
    sendMessage: vi.fn(() => Promise.resolve({})),
    createSession: vi.fn(),
    getSession: vi.fn(),
  },
}));

function createAgentEvent(agentName: string, text: string, timestamp?: number): AgentEvent {
  return {
    type: 'agent_step',
    agentName,
    data: { content: text },
    timestamp: timestamp || Date.now(),
  };
}

describe('AgentChat - Input Detection', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('detects input waiting on question marks', () => {
    const onWaitingForInput = vi.fn();
    const events: AgentEvent[] = [
      createAgentEvent('user', 'Start the pipeline'),
      createAgentEvent('root_agent', 'Should I proceed with the Google Pixel campaign? The configuration looks correct.'),
    ];

    render(
      <AgentChat
        sessionId="test-session"
        events={events}
        onWaitingForInput={onWaitingForInput}
      />
    );

    expect(onWaitingForInput).toHaveBeenCalledWith(true);
  });

  it('detects input waiting on "select" keyword', () => {
    const onWaitingForInput = vi.fn();
    const events: AgentEvent[] = [
      createAgentEvent('root_agent', 'Please select the trends you want to analyze for this campaign. Here are the available options:'),
    ];

    render(
      <AgentChat
        sessionId="test-session"
        events={events}
        onWaitingForInput={onWaitingForInput}
      />
    );

    expect(onWaitingForInput).toHaveBeenCalledWith(true);
  });

  it('detects input waiting on "would you like" keyword', () => {
    const onWaitingForInput = vi.fn();
    const events: AgentEvent[] = [
      createAgentEvent('root_agent', 'Would you like me to proceed with the current configuration'),
    ];

    render(
      <AgentChat
        sessionId="test-session"
        events={events}
        onWaitingForInput={onWaitingForInput}
      />
    );

    expect(onWaitingForInput).toHaveBeenCalledWith(true);
  });

  it('does not detect input waiting for non-interactive messages', () => {
    const onWaitingForInput = vi.fn();
    const events: AgentEvent[] = [
      createAgentEvent('root_agent', 'Starting research pipeline now. This will take a few minutes to complete the full analysis.'),
    ];

    render(
      <AgentChat
        sessionId="test-session"
        events={events}
        onWaitingForInput={onWaitingForInput}
      />
    );

    expect(onWaitingForInput).toHaveBeenCalledWith(false);
  });

  it('shows "Awaiting response" badge when waiting for input', () => {
    const events: AgentEvent[] = [
      createAgentEvent('root_agent', 'Do you approve this ad copy draft? It scored 85/100 on the evaluation rubric.'),
    ];

    render(
      <AgentChat sessionId="test-session" events={events} />
    );

    expect(screen.getByText('Awaiting response')).toBeInTheDocument();
  });

  it('shows quick action buttons when waiting for approval', () => {
    const events: AgentEvent[] = [
      createAgentEvent('root_agent', 'Here is the final ad copy. Does it look good to proceed with visual generation?'),
    ];

    render(
      <AgentChat sessionId="test-session" events={events} />
    );

    expect(screen.getByText('Approve All')).toBeInTheDocument();
    expect(screen.getByText('Revise')).toBeInTheDocument();
  });
});

describe('Parallel Stream Matching', () => {
  it('matches events using substring matching for yt streams', () => {
    // This tests that our stream matching approach works
    const events: AgentEvent[] = [
      createAgentEvent('yt_analysis_generator_agent', 'Analyzing YouTube trends'),
      createAgentEvent('yt_web_planner', 'Planning web search'),
      createAgentEvent('yt_sequential_planner', 'Sequential planning'),
    ];

    const getStreamEvents = (keywords: string[]) =>
      events.filter(e => keywords.some(kw => e.agentName.toLowerCase().includes(kw)));

    const ytEvents = getStreamEvents(['yt_sequential', 'yt_analysis', 'yt_web']);
    expect(ytEvents).toHaveLength(3);
  });

  it('matches events using substring matching for gs streams', () => {
    const events: AgentEvent[] = [
      createAgentEvent('gs_web_planner', 'Planning Google search'),
      createAgentEvent('gs_web_searcher', 'Searching'),
      createAgentEvent('gs_sequential_planner', 'Sequential planning'),
    ];

    const getStreamEvents = (keywords: string[]) =>
      events.filter(e => keywords.some(kw => e.agentName.toLowerCase().includes(kw)));

    const gsEvents = getStreamEvents(['gs_sequential', 'gs_web']);
    expect(gsEvents).toHaveLength(3);
  });

  it('matches events using substring matching for campaign streams', () => {
    const events: AgentEvent[] = [
      createAgentEvent('campaign_web_planner', 'Planning campaign research'),
      createAgentEvent('campaign_web_searcher', 'Searching'),
      createAgentEvent('ca_sequential_planner', 'Sequential planning'),
    ];

    const getStreamEvents = (keywords: string[]) =>
      events.filter(e => keywords.some(kw => e.agentName.toLowerCase().includes(kw)));

    const caEvents = getStreamEvents(['ca_sequential', 'campaign_web']);
    expect(caEvents).toHaveLength(3);
  });

  it('does not cross-match between different streams', () => {
    const events: AgentEvent[] = [
      createAgentEvent('yt_web_planner', 'YouTube planning'),
      createAgentEvent('gs_web_planner', 'Google Search planning'),
      createAgentEvent('campaign_web_planner', 'Campaign planning'),
    ];

    const getStreamEvents = (keywords: string[]) =>
      events.filter(e => keywords.some(kw => e.agentName.toLowerCase().includes(kw)));

    expect(getStreamEvents(['yt_sequential', 'yt_analysis', 'yt_web'])).toHaveLength(1);
    expect(getStreamEvents(['gs_sequential', 'gs_web'])).toHaveLength(1);
    expect(getStreamEvents(['ca_sequential', 'campaign_web'])).toHaveLength(1);
  });
});
