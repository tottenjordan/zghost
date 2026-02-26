import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '../test-utils';
import userEvent from '@testing-library/user-event';
import React from 'react';

// Mock navigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...(actual as object),
    useNavigate: () => mockNavigate,
    Link: ({ to, children, ...props }: any) => <a href={to} {...props}>{children}</a>,
  };
});

// Mock campaign store
const mockStoreState = {
  config: { brand: 'TestBrand', target_product: 'TestProduct', target_audience: '', key_selling_points: '' },
  selectedSearchTrends: [{ rank: 1, title: 'Test Trend', relatedQueries: '' }] as any[],
  selectedYtTrends: [] as any[],
  activeRubrics: [] as any[],
  sessions: [] as any[],
  activeSessionIndex: -1,
  sessionId: null as string | null,
  pipelineStatus: 'idle' as string,
  commercialDuration: 30 as 10 | 15 | 30,
  autoStart: false,
  addSession: vi.fn(),
  removeSession: vi.fn(),
  setActiveSession: vi.fn(),
  setSessionId: vi.fn(),
  setPipelineStatus: vi.fn(),
  setCommercialDuration: vi.fn(),
  setAutoStart: vi.fn(),
  isReadyToLaunch: vi.fn(() => ({ ready: true, missing: [] })),
};

vi.mock('../../stores/campaignStore', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...(actual as object),
    useCampaignStore: () => mockStoreState,
  };
});

// Mock useOrchestration hook
const mockOrchestration = {
  status: null as any,
  loading: false,
  error: null,
  refetch: vi.fn(),
  events: [] as any[],
  allEvents: [] as any[],
  getAgentEvents: vi.fn(() => []),
  clearEvents: vi.fn(),
  isConnected: false,
  sessionState: {} as Record<string, any>,
  changedKeys: new Set<string>(),
  filters: {},
  updateFilters: vi.fn(),
  clearFilters: vi.fn(),
  selectedAgent: null as string | null,
  setSelectedAgent: vi.fn(),
  isPaused: false,
  togglePause: vi.fn(),
};

vi.mock('../../features/orchestration/useOrchestration', () => ({
  useOrchestration: () => mockOrchestration,
}));

// Mock API
const mockApi = {
  createSession: vi.fn(),
  sendMessage: vi.fn(),
  getSession: vi.fn(),
};

vi.mock('../../services/api', () => ({
  api: {
    createSession: (...args: any[]) => mockApi.createSession(...args),
    sendMessage: (...args: any[]) => mockApi.sendMessage(...args),
    getSession: (...args: any[]) => mockApi.getSession(...args),
  },
}));

// Mock heavy sub-components to isolate orchestration-level tests
vi.mock('../../features/orchestration/PipelineGraph', () => ({
  PipelineGraph: () => <div data-testid="pipeline-graph">PipelineGraph</div>,
}));

vi.mock('../../features/orchestration/DAGTimeline', () => ({
  DAGTimeline: ({ events }: any) => (
    <div data-testid="dag-timeline">
      {events?.map((e: any, i: number) => (
        <div key={i} data-testid={`timeline-event-${i}`}>{e.agentName}</div>
      ))}
    </div>
  ),
}));

vi.mock('../../features/orchestration/EventStream', () => ({
  EventStream: () => <div data-testid="event-stream">EventStream</div>,
}));

vi.mock('../../features/orchestration/TaskDrillDown', () => ({
  TaskDrillDown: () => <div data-testid="task-drilldown">TaskDrillDown</div>,
}));

vi.mock('../../features/orchestration/ParallelStreamView', () => ({
  ParallelStreamView: ({ streams }: any) => (
    <div data-testid="parallel-stream-view">
      {streams?.map((s: any) => (
        <div key={s.id} data-testid={`stream-${s.id}`}>{s.name}: {s.status}</div>
      ))}
    </div>
  ),
}));

vi.mock('../../features/orchestration/SessionStatePanel', () => ({
  SessionStatePanel: ({ state }: any) => (
    <div data-testid="session-state-panel">
      {Object.entries(state || {}).map(([key, val]) => (
        <div key={key} data-testid={`state-${key}`}>{key}: {String(val)}</div>
      ))}
    </div>
  ),
}));

vi.mock('../../features/orchestration/AgentChat', () => ({
  AgentChat: () => <div data-testid="agent-chat">AgentChat</div>,
}));

vi.mock('../../features/orchestration/ResultsGallery', () => ({
  ResultsGallery: () => <div data-testid="results-gallery">ResultsGallery</div>,
}));

vi.mock('../../features/orchestration/EvaluationPanel', () => ({
  EvaluationPanel: () => <div data-testid="evaluation-panel">EvaluationPanel</div>,
}));

vi.mock('../../features/orchestration/PipelineControls', () => ({
  PipelineControls: ({ onStart, readyToLaunch }: any) => (
    <div data-testid="pipeline-controls">
      <button
        onClick={() => onStart(1)}
        disabled={!readyToLaunch}
        data-testid="start-pipeline-btn"
      >
        Start Pipeline
      </button>
    </div>
  ),
}));

vi.mock('../../features/orchestration/SessionTabBar', () => ({
  SessionTabBar: () => <div data-testid="session-tab-bar">SessionTabBar</div>,
}));

const { OrchestrationPage } = await import('../../features/orchestration/OrchestrationPage');

describe('CUJ 2: Orchestration Dashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    mockStoreState.config = { brand: 'TestBrand', target_product: 'TestProduct', target_audience: '', key_selling_points: '' };
    mockStoreState.selectedSearchTrends = [{ rank: 1, title: 'Test Trend', relatedQueries: '' }];
    mockStoreState.selectedYtTrends = [];
    mockStoreState.activeRubrics = [];
    mockStoreState.sessions = [];
    mockStoreState.activeSessionIndex = -1;
    mockStoreState.sessionId = null;
    mockStoreState.pipelineStatus = 'idle';
    mockStoreState.commercialDuration = 30;
    mockStoreState.isReadyToLaunch.mockReturnValue({ ready: true, missing: [] });

    mockOrchestration.status = null;
    mockOrchestration.events = [];
    mockOrchestration.allEvents = [];
    mockOrchestration.sessionState = {};
    mockOrchestration.changedKeys = new Set();
    mockOrchestration.selectedAgent = null;

    mockApi.createSession.mockResolvedValue({ session_id: 'test-session-123' });
    mockApi.sendMessage.mockResolvedValue({ response: 'ok' });
  });

  it('renders timeline and agent graph tabs', () => {
    render(<OrchestrationPage />);

    expect(screen.getByText('Timeline')).toBeInTheDocument();
    expect(screen.getByText('Agent Graph')).toBeInTheDocument();
  });

  it('shows running agents on timeline', () => {
    mockOrchestration.events = [
      { type: 'agent_step', agentName: 'trend_agent', timestamp: Date.now(), data: {} },
      { type: 'agent_step', agentName: 'research_agent', timestamp: Date.now(), data: {} },
    ];

    render(<OrchestrationPage />);

    // Timeline is the default tab — DAGTimeline receives events
    expect(screen.getByTestId('dag-timeline')).toBeInTheDocument();
    expect(screen.getByText('trend_agent')).toBeInTheDocument();
    expect(screen.getByText('research_agent')).toBeInTheDocument();
  });

  it('shows agent graph view when tab clicked', async () => {
    const user = userEvent.setup();
    render(<OrchestrationPage />);

    await user.click(screen.getByText('Agent Graph'));

    expect(screen.getByTestId('pipeline-graph')).toBeInTheDocument();
  });

  it('shows 6 detail panel tabs', () => {
    render(<OrchestrationPage />);

    expect(screen.getByText('Chat')).toBeInTheDocument();
    expect(screen.getByText('Results')).toBeInTheDocument();
    expect(screen.getByText('Eval')).toBeInTheDocument();
    expect(screen.getByText('Details')).toBeInTheDocument();
    expect(screen.getByText('Streams')).toBeInTheDocument();
    expect(screen.getByText('State')).toBeInTheDocument();
  });

  it('shows chat tab with AgentChat by default', () => {
    render(<OrchestrationPage />);

    // Chat is the default detail panel tab
    expect(screen.getByTestId('agent-chat')).toBeInTheDocument();
  });

  it('shows agent status in parallel stream view', async () => {
    const user = userEvent.setup();

    // Provide events matching YT/GS/Campaign keywords
    mockOrchestration.events = [
      { type: 'agent_step', agentName: 'yt_sequential_planner', timestamp: Date.now(), data: {} },
      { type: 'agent_step', agentName: 'gs_web_planner', timestamp: Date.now(), data: {} },
      { type: 'agent_step', agentName: 'campaign_web_planner', timestamp: Date.now(), data: {} },
    ];
    mockStoreState.sessionId = 'test-session';

    render(<OrchestrationPage />);

    // Switch to Streams tab
    await user.click(screen.getByText('Streams'));

    await waitFor(() => {
      expect(screen.getByTestId('parallel-stream-view')).toBeInTheDocument();
    });
  });

  it('exposes session state panel with state values', async () => {
    const user = userEvent.setup();
    mockOrchestration.sessionState = {
      brand: 'TestBrand',
      commercial_duration: 30,
      target_product: 'TestProduct',
    };

    render(<OrchestrationPage />);

    // Switch to State tab
    await user.click(screen.getByText('State'));

    await waitFor(() => {
      expect(screen.getByTestId('session-state-panel')).toBeInTheDocument();
      expect(screen.getByText(/brand: TestBrand/)).toBeInTheDocument();
      expect(screen.getByText(/commercial_duration: 30/)).toBeInTheDocument();
    });
  });

  it('dispatches job with campaign config on start', async () => {
    const user = userEvent.setup();
    render(<OrchestrationPage />);

    await user.click(screen.getByTestId('start-pipeline-btn'));

    await waitFor(() => {
      expect(mockApi.createSession).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(mockApi.sendMessage).toHaveBeenCalled();
    });

    // Verify campaign metadata was sent
    const sendCalls = mockApi.sendMessage.mock.calls;
    const messages = sendCalls.map((c: any[]) => c[0]?.message || '');
    expect(messages.some((m: string) => m.includes('TestBrand'))).toBe(true);
    expect(messages.some((m: string) => m.includes('Test Trend'))).toBe(true);
  });

  it('shows page heading', () => {
    render(<OrchestrationPage />);

    expect(screen.getByText('Agent Orchestration')).toBeInTheDocument();
  });

  it.skip('restricts access to super users — NOT IMPLEMENTED', () => {
    // TODO: No auth/role system exists in the frontend.
    // CUJ 2.1 specifies that only super users should access orchestration.
    // Implement role-based access control and guard this route.
  });
});
