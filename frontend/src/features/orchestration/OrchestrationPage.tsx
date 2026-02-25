import { useState, useCallback } from 'react';
import { PipelineGraph } from './PipelineGraph';
import { EventStream } from './EventStream';
import { TaskDrillDown } from './TaskDrillDown';
import { ParallelStreamView } from './ParallelStreamView';
import { PipelineControls } from './PipelineControls';
import { useOrchestration } from './useOrchestration';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../components/ui/Tabs';
import type { AgentEventType } from '../../types/agents';

// Mock session ID for development
const MOCK_SESSION_ID = 'dev-session-123';
const MOCK_STREAM_URL = null; // Replace with actual stream URL when available

export function OrchestrationPage() {
  const [sessionId] = useState<string | null>(MOCK_SESSION_ID);
  const [streamUrl] = useState<string | null>(MOCK_STREAM_URL);
  const [isRunning, setIsRunning] = useState(false);

  const {
    status,
    error,
    refetch,
    events,
    getAgentEvents,
    selectedAgent,
    setSelectedAgent,
    updateFilters,
    clearFilters,
    isPaused,
    togglePause,
  } = useOrchestration(sessionId, streamUrl);

  const handleStart = useCallback((parallelCount: number) => {
    console.log('Starting pipeline with', parallelCount, 'parallel streams');
    setIsRunning(true);
    // TODO: Call API to start pipeline
  }, []);

  const handleStop = useCallback(() => {
    console.log('Stopping pipeline');
    setIsRunning(false);
    // TODO: Call API to stop pipeline
  }, []);

  const handleRefresh = useCallback(() => {
    refetch();
    clearFilters();
  }, [refetch, clearFilters]);

  const handleFilterAgent = useCallback(
    (agentName: string) => {
      updateFilters({ agentName });
    },
    [updateFilters]
  );

  const handleFilterEventType = useCallback(
    (eventType: AgentEventType) => {
      updateFilters({ eventType });
    },
    [updateFilters]
  );

  const handleSearch = useCallback(
    (searchTerm: string) => {
      updateFilters({ searchTerm });
    },
    [updateFilters]
  );

  // Mock parallel streams for demo
  const parallelStreams = [
    {
      id: 'stream-1',
      name: 'YouTube Research Stream',
      status: 'running' as const,
      progress: 65,
      currentStage: 'web_scraping',
      events: getAgentEvents('yt_sequential_planner'),
    },
    {
      id: 'stream-2',
      name: 'Google Search Stream',
      status: 'completed' as const,
      progress: 100,
      events: getAgentEvents('gs_sequential_planner'),
    },
    {
      id: 'stream-3',
      name: 'Campaign Research Stream',
      status: 'running' as const,
      progress: 45,
      currentStage: 'analysis',
      events: getAgentEvents('ca_sequential_planner'),
    },
  ];

  const selectedAgentState = selectedAgent ? status?.agents[selectedAgent] : undefined;
  const selectedAgentEvents = selectedAgent ? getAgentEvents(selectedAgent) : [];

  return (
    <div className="flex flex-col h-full gap-4">
      {/* Header */}
      <div>
        <h1 className="mb-2 text-2xl font-bold">Agent Orchestration</h1>
        <p className="text-zinc-400 text-sm">
          Monitor and control the agent pipeline execution in real-time.
        </p>
      </div>

      {/* Pipeline Controls */}
      <PipelineControls
        isRunning={isRunning}
        sessionId={sessionId}
        onStart={handleStart}
        onStop={handleStop}
        onRefresh={handleRefresh}
      />

      {/* Connection Status */}
      {error && (
        <div className="p-3 bg-red-950/50 border border-red-800 rounded text-red-300 text-sm">
          Error: {error instanceof Error ? error.message : 'Failed to connect to agent service'}
        </div>
      )}

      {/* Main content area - split layout */}
      <div className="flex-1 grid grid-cols-3 gap-4 min-h-0">
        {/* Left: Pipeline Graph (2 columns) */}
        <div className="col-span-2 border border-zinc-800 rounded-lg overflow-hidden">
          <PipelineGraph
            status={status}
            events={events}
            onSelectAgent={setSelectedAgent}
          />
        </div>

        {/* Right: Drill-down panel or Parallel streams (1 column) */}
        <div className="overflow-hidden">
          <Tabs defaultValue="details">
            <TabsList className="w-full">
              <TabsTrigger value="details">Agent Details</TabsTrigger>
              <TabsTrigger value="parallel">Parallel Streams</TabsTrigger>
            </TabsList>

            <TabsContent value="details">
              {selectedAgent ? (
                <TaskDrillDown
                  agentName={selectedAgent}
                  agentState={selectedAgentState}
                  events={selectedAgentEvents}
                  onClose={() => setSelectedAgent(null)}
                />
              ) : (
                <div className="h-full flex items-center justify-center text-zinc-500 text-sm border border-zinc-800 rounded-lg bg-zinc-900">
                  Select an agent node to view details
                </div>
              )}
            </TabsContent>

            <TabsContent value="parallel">
              <ParallelStreamView streams={parallelStreams} />
            </TabsContent>
          </Tabs>
        </div>
      </div>

      {/* Bottom: Event Stream */}
      <div className="h-80 flex-shrink-0">
        <EventStream
          events={events}
          isPaused={isPaused}
          onTogglePause={togglePause}
          onFilterAgent={handleFilterAgent}
          onFilterEventType={handleFilterEventType}
          onSearch={handleSearch}
        />
      </div>
    </div>
  );
}
