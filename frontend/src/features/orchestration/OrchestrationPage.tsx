import { useState, useCallback } from 'react';
import { PipelineGraph } from './PipelineGraph';
import { EventStream } from './EventStream';
import { TaskDrillDown } from './TaskDrillDown';
import { ParallelStreamView } from './ParallelStreamView';
import { SessionStatePanel } from './SessionStatePanel';
import { PipelineControls } from './PipelineControls';
import { useOrchestration } from './useOrchestration';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../components/ui/Tabs';
import { api } from '../../services/api';
import { useCampaignStore } from '../../stores/campaignStore';
import type { AgentEventType } from '../../types/agents';

const APP_NAME = import.meta.env.VITE_APP_NAME || 'trends_and_insights_agent';
const USER_ID = 'frontend-user';

export function OrchestrationPage() {
  const [streamUrl] = useState<string | null>(null);
  const [startError, setStartError] = useState<string | null>(null);

  // Get campaign store state and actions
  const {
    config,
    selectedSearchTrends,
    selectedYtTrends,
    activeRubric,
    sessionId,
    pipelineStatus,
    setSessionId,
    setPipelineStatus,
    isReadyToLaunch,
  } = useCampaignStore();

  const isRunning = pipelineStatus === 'running';

  const {
    status,
    refetch,
    events,
    getAgentEvents,
    sessionState,
    changedKeys,
    selectedAgent,
    setSelectedAgent,
    updateFilters,
    clearFilters,
    isPaused,
    togglePause,
  } = useOrchestration(sessionId, streamUrl);

  const handleStart = useCallback(async (parallelCount: number) => {
    setStartError(null);
    setPipelineStatus('running');
    try {
      // Create a real ADK session
      const session = await api.createSession(APP_NAME, USER_ID);
      setSessionId(session.session_id);

      // Build campaign metadata message
      const campaignMetadata = `Campaign for ${config.brand || '[brand]'} ${config.target_product || '[product]'}. Target audience: ${config.target_audience || '[not specified]'}. Key selling points: ${config.key_selling_points || '[not specified]'}`;

      // Build trend selections message
      const searchTrendTitles = selectedSearchTrends.map((t) => t.title).join(', ');
      const ytTrendTitles = selectedYtTrends.map((t) => t.title).join(', ');
      const trendSelections = `Selected Google trends: ${searchTrendTitles || 'none'}. Selected YouTube trends: ${ytTrendTitles || 'none'}.`;

      // Build rubric guidance message (if active)
      let rubricGuidance = '';
      if (activeRubric) {
        const criteriaDesc = activeRubric.criteria
          .map((c) => `${c.name} (weight: ${c.weight})`)
          .join(', ');
        rubricGuidance = `Evaluate outputs against these criteria: ${criteriaDesc}`;
      }

      // Send campaign metadata
      await api.sendMessage({
        app_name: APP_NAME,
        user_id: USER_ID,
        session_id: session.session_id,
        message: campaignMetadata,
      });

      // Send trend selections
      await api.sendMessage({
        app_name: APP_NAME,
        user_id: USER_ID,
        session_id: session.session_id,
        message: trendSelections,
      });

      // Send rubric guidance if active
      if (rubricGuidance) {
        await api.sendMessage({
          app_name: APP_NAME,
          user_id: USER_ID,
          session_id: session.session_id,
          message: rubricGuidance,
        });
      }

      // Send pipeline start command
      await api.sendMessage({
        app_name: APP_NAME,
        user_id: USER_ID,
        session_id: session.session_id,
        message: `start the full pipeline with ${parallelCount} parallel stream(s)`,
      });
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to start pipeline';
      setStartError(msg);
      setPipelineStatus('error');
    }
  }, [config, selectedSearchTrends, selectedYtTrends, activeRubric, setSessionId, setPipelineStatus]);

  const handleStop = useCallback(() => {
    setSessionId(null);
    setPipelineStatus('idle');
    setStartError(null);
  }, [setSessionId, setPipelineStatus]);

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

  // Build parallel streams from real event data
  const ytEvents = getAgentEvents('yt_sequential_planner');
  const gsEvents = getAgentEvents('gs_sequential_planner');
  const caEvents = getAgentEvents('ca_sequential_planner');

  const parallelStreams = [
    {
      id: 'stream-1',
      name: 'YouTube Research Stream',
      status: ytEvents.length > 0 ? ('running' as const) : ('pending' as const),
      progress: Math.min(100, ytEvents.length * 10),
      currentStage: ytEvents.length > 5 ? 'web_scraping' : ytEvents.length > 0 ? 'planning' : undefined,
      events: ytEvents,
    },
    {
      id: 'stream-2',
      name: 'Google Search Stream',
      status: gsEvents.length > 0 ? ('running' as const) : ('pending' as const),
      progress: Math.min(100, gsEvents.length * 10),
      currentStage: gsEvents.length > 5 ? 'searching' : gsEvents.length > 0 ? 'planning' : undefined,
      events: gsEvents,
    },
    {
      id: 'stream-3',
      name: 'Campaign Research Stream',
      status: caEvents.length > 0 ? ('running' as const) : ('pending' as const),
      progress: Math.min(100, caEvents.length * 10),
      currentStage: caEvents.length > 5 ? 'analysis' : caEvents.length > 0 ? 'planning' : undefined,
      events: caEvents,
    },
  ].filter(stream => stream.events.length > 0 || sessionId !== null);

  const selectedAgentState = selectedAgent ? status?.agents[selectedAgent] : undefined;
  const selectedAgentEvents = selectedAgent ? getAgentEvents(selectedAgent) : [];

  // Check if ready to launch
  const { ready, missing } = isReadyToLaunch();

  return (
    <div className="flex flex-col h-full gap-4">
      {/* Header */}
      <div>
        <h1 className="mb-2 text-2xl font-bold">Agent Orchestration</h1>
        <p className="text-zinc-400 text-sm">
          Monitor and control the agent pipeline execution in real-time.
        </p>
      </div>

      {/* Pre-launch Summary */}
      <div className="p-4 bg-zinc-900 border border-zinc-800 rounded-lg">
        <h2 className="text-sm font-semibold mb-3 text-zinc-300">Campaign Configuration</h2>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-zinc-500">Brand/Product:</span>{' '}
            {config.brand || config.target_product ? (
              <span className="text-zinc-200">
                {config.brand} {config.target_product}
              </span>
            ) : (
              <span className="text-amber-400">Not set</span>
            )}
          </div>
          <div>
            <span className="text-zinc-500">Trends Selected:</span>{' '}
            {selectedSearchTrends.length > 0 || selectedYtTrends.length > 0 ? (
              <span className="text-zinc-200">
                {selectedSearchTrends.length} Google + {selectedYtTrends.length} YouTube
              </span>
            ) : (
              <span className="text-amber-400">None</span>
            )}
          </div>
          <div className="col-span-2">
            <span className="text-zinc-500">Active Rubric:</span>{' '}
            {activeRubric ? (
              <span className="text-zinc-200">{activeRubric.name}</span>
            ) : (
              <span className="text-zinc-500">None - using defaults</span>
            )}
          </div>
        </div>
      </div>

      {/* Pipeline Controls */}
      <PipelineControls
        isRunning={isRunning}
        sessionId={sessionId}
        readyToLaunch={ready}
        missingItems={missing}
        onStart={handleStart}
        onStop={handleStop}
        onRefresh={handleRefresh}
      />

      {/* Connection Status */}
      {startError && (
        <div className="p-3 bg-red-950/50 border border-red-800 rounded text-red-300 text-sm">
          Error: {startError}
        </div>
      )}

      {/* Main content area - split layout */}
      <div className="flex-1 grid grid-cols-3 gap-4 min-h-0">
        {/* Left: Pipeline Graph (2 columns) */}
        <div className="col-span-2 border border-zinc-800 rounded-lg overflow-hidden min-h-[500px]">
          <PipelineGraph
            status={status}
            events={events}
            onSelectAgent={setSelectedAgent}
          />
        </div>

        {/* Right: Drill-down panel or Parallel streams (1 column) */}
        <div className="overflow-hidden">
          <Tabs defaultValue="details">
            <TabsList className="w-full grid grid-cols-3">
              <TabsTrigger value="details">Agent Details</TabsTrigger>
              <TabsTrigger value="parallel">Parallel Streams</TabsTrigger>
              <TabsTrigger value="state">Session State</TabsTrigger>
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

            <TabsContent value="state">
              <SessionStatePanel state={sessionState} changedKeys={changedKeys} />
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
