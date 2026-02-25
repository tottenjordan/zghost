import { useState, useCallback } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { PipelineGraph } from './PipelineGraph';
import { DAGTimeline } from './DAGTimeline';
import { EventStream } from './EventStream';
import { TaskDrillDown } from './TaskDrillDown';
import { ParallelStreamView } from './ParallelStreamView';
import { SessionStatePanel } from './SessionStatePanel';
import { PipelineControls } from './PipelineControls';
import { SessionTabBar } from './SessionTabBar';
import { useOrchestration } from './useOrchestration';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../components/ui/Tabs';
import { api } from '../../services/api';
import { useCampaignStore } from '../../stores/campaignStore';
import { cn } from '../../lib/utils';
import type { AgentEventType } from '../../types/agents';

const APP_NAME = import.meta.env.VITE_APP_NAME || 'trends_and_insights_agent';
const USER_ID = 'frontend-user';

export function OrchestrationPage() {
  const [streamUrl] = useState<string | null>(null);
  const [startError, setStartError] = useState<string | null>(null);
  const [eventStreamOpen, setEventStreamOpen] = useState(true);

  const {
    config,
    selectedSearchTrends,
    selectedYtTrends,
    activeRubric,
    sessions,
    activeSessionIndex,
    sessionId,
    pipelineStatus,
    addSession,
    removeSession,
    setActiveSession,
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
    try {
      const session = await api.createSession(APP_NAME, USER_ID);

      // Create new session entry
      const newSession = {
        id: `session-${Date.now()}`,
        sessionId: session.session_id,
        label: `Run ${sessions.length + 1}`,
        status: 'running' as const,
        startedAt: Date.now(),
      };

      addSession(newSession);

      const campaignMetadata = `Campaign for ${config.brand || '[brand]'} ${config.target_product || '[product]'}. Target audience: ${config.target_audience || '[not specified]'}. Key selling points: ${config.key_selling_points || '[not specified]'}`;

      const searchTrendTitles = selectedSearchTrends.map((t) => t.title).join(', ');
      const ytTrendTitles = selectedYtTrends.map((t) => t.title).join(', ');
      const trendSelections = `Selected Google trends: ${searchTrendTitles || 'none'}. Selected YouTube trends: ${ytTrendTitles || 'none'}.`;

      let rubricGuidance = '';
      if (activeRubric) {
        const criteriaDesc = activeRubric.criteria
          .map((c) => `${c.name} (weight: ${c.weight})`)
          .join(', ');
        rubricGuidance = `Evaluate outputs against these criteria: ${criteriaDesc}`;
      }

      await api.sendMessage({
        app_name: APP_NAME, user_id: USER_ID,
        session_id: session.session_id, message: campaignMetadata,
      });

      await api.sendMessage({
        app_name: APP_NAME, user_id: USER_ID,
        session_id: session.session_id, message: trendSelections,
      });

      if (rubricGuidance) {
        await api.sendMessage({
          app_name: APP_NAME, user_id: USER_ID,
          session_id: session.session_id, message: rubricGuidance,
        });
      }

      await api.sendMessage({
        app_name: APP_NAME, user_id: USER_ID,
        session_id: session.session_id,
        message: `start the full pipeline with ${parallelCount} parallel stream(s)`,
      });
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to start pipeline';
      setStartError(msg);
      setPipelineStatus('error');
    }
  }, [config, selectedSearchTrends, selectedYtTrends, activeRubric, sessions, addSession, setPipelineStatus]);

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
    (agentName: string) => updateFilters({ agentName }),
    [updateFilters]
  );

  const handleFilterEventType = useCallback(
    (eventType: AgentEventType) => updateFilters({ eventType }),
    [updateFilters]
  );

  const handleSearch = useCallback(
    (searchTerm: string) => updateFilters({ searchTerm }),
    [updateFilters]
  );

  // Parallel streams
  const ytEvents = getAgentEvents('yt_sequential_planner');
  const gsEvents = getAgentEvents('gs_sequential_planner');
  const caEvents = getAgentEvents('ca_sequential_planner');

  const parallelStreams = [
    { id: 'stream-1', name: 'YouTube Research', status: ytEvents.length > 0 ? ('running' as const) : ('pending' as const), progress: Math.min(100, ytEvents.length * 10), currentStage: ytEvents.length > 5 ? 'web_scraping' : ytEvents.length > 0 ? 'planning' : undefined, events: ytEvents },
    { id: 'stream-2', name: 'Google Search', status: gsEvents.length > 0 ? ('running' as const) : ('pending' as const), progress: Math.min(100, gsEvents.length * 10), currentStage: gsEvents.length > 5 ? 'searching' : gsEvents.length > 0 ? 'planning' : undefined, events: gsEvents },
    { id: 'stream-3', name: 'Campaign Research', status: caEvents.length > 0 ? ('running' as const) : ('pending' as const), progress: Math.min(100, caEvents.length * 10), currentStage: caEvents.length > 5 ? 'analysis' : caEvents.length > 0 ? 'planning' : undefined, events: caEvents },
  ].filter(stream => stream.events.length > 0 || sessionId !== null);

  const selectedAgentState = selectedAgent ? status?.agents[selectedAgent] : undefined;
  const selectedAgentEvents = selectedAgent ? getAgentEvents(selectedAgent) : [];
  const { ready, missing } = isReadyToLaunch();
  const totalTrends = selectedSearchTrends.length + selectedYtTrends.length;

  return (
    <div className="flex flex-col h-full gap-3">
      {/* Compact header + config summary */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold">Agent Orchestration</h1>
          <p className="text-xs text-zinc-500 mt-0.5">Monitor and control the agent pipeline</p>
        </div>
        <div className="flex items-center gap-3 text-xs">
          <span className={cn('px-2 py-0.5 rounded border', config.brand ? 'border-green-700/50 bg-green-950/30 text-green-400' : 'border-amber-700/50 bg-amber-950/30 text-amber-400')}>
            {config.brand || config.target_product || 'No brand'}
          </span>
          <span className={cn('px-2 py-0.5 rounded border', totalTrends > 0 ? 'border-green-700/50 bg-green-950/30 text-green-400' : 'border-amber-700/50 bg-amber-950/30 text-amber-400')}>
            {totalTrends > 0 ? `${totalTrends} trends` : 'No trends'}
          </span>
          <span className={cn('px-2 py-0.5 rounded border', activeRubric ? 'border-green-700/50 bg-green-950/30 text-green-400' : 'border-zinc-700/50 bg-zinc-800/50 text-zinc-500')}>
            {activeRubric?.name || 'Default rubric'}
          </span>
        </div>
      </div>

      {/* Session Tab Bar */}
      <SessionTabBar
        sessions={sessions}
        activeSessionIndex={activeSessionIndex}
        onSelectSession={setActiveSession}
        onRemoveSession={removeSession}
        onNewSession={() => handleStart(1)}
        isRunning={isRunning}
      />

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

      {startError && (
        <div className="p-2 bg-red-950/50 border border-red-800 rounded text-red-300 text-xs">
          {startError}
        </div>
      )}

      {/* Main: Timeline + Detail panel */}
      <div className="flex-1 grid grid-cols-3 gap-3 min-h-0">
        {/* Left: Timeline / Graph (2 cols) */}
        <div className="col-span-2 border border-zinc-800 rounded-lg overflow-hidden flex flex-col min-h-[400px]">
          <Tabs defaultValue="timeline">
            <TabsList className="w-full grid grid-cols-2">
              <TabsTrigger value="timeline">Timeline</TabsTrigger>
              <TabsTrigger value="graph">Agent Graph</TabsTrigger>
            </TabsList>

            <TabsContent value="timeline" className="flex-1 p-3 overflow-auto">
              <DAGTimeline
                events={events}
                onSelectAgent={setSelectedAgent}
                selectedAgent={selectedAgent}
              />
            </TabsContent>

            <TabsContent value="graph" className="flex-1 min-h-[400px]">
              <PipelineGraph
                status={status}
                events={events}
                onSelectAgent={setSelectedAgent}
              />
            </TabsContent>
          </Tabs>
        </div>

        {/* Right: Detail panel (1 col) */}
        <div className="border border-zinc-800 rounded-lg overflow-hidden flex flex-col">
          <Tabs defaultValue="details">
            <TabsList className="w-full grid grid-cols-3">
              <TabsTrigger value="details">Details</TabsTrigger>
              <TabsTrigger value="streams">Streams</TabsTrigger>
              <TabsTrigger value="state">State</TabsTrigger>
            </TabsList>

            <TabsContent value="details" className="flex-1 overflow-auto">
              {selectedAgent ? (
                <TaskDrillDown
                  agentName={selectedAgent}
                  agentState={selectedAgentState}
                  events={selectedAgentEvents}
                  onClose={() => setSelectedAgent(null)}
                />
              ) : (
                <div className="flex items-center justify-center p-8 text-zinc-500 text-sm">
                  Click an agent to view details
                </div>
              )}
            </TabsContent>

            <TabsContent value="streams" className="flex-1 overflow-auto">
              <ParallelStreamView streams={parallelStreams} />
            </TabsContent>

            <TabsContent value="state" className="flex-1 overflow-auto">
              <SessionStatePanel state={sessionState} changedKeys={changedKeys} />
            </TabsContent>
          </Tabs>
        </div>
      </div>

      {/* Bottom: Collapsible Event Stream */}
      <div className="flex-shrink-0">
        <button
          onClick={() => setEventStreamOpen(!eventStreamOpen)}
          className="flex w-full items-center gap-2 px-3 py-1.5 text-xs font-medium text-zinc-400 hover:text-zinc-300 border border-zinc-800 rounded-t-lg bg-zinc-900/50"
        >
          {eventStreamOpen ? <ChevronDown className="h-3 w-3" /> : <ChevronUp className="h-3 w-3" />}
          Event Stream ({events.length} events)
        </button>
        {eventStreamOpen && (
          <div className="h-48 border border-t-0 border-zinc-800 rounded-b-lg overflow-hidden">
            <EventStream
              events={events}
              isPaused={isPaused}
              onTogglePause={togglePause}
              onFilterAgent={handleFilterAgent}
              onFilterEventType={handleFilterEventType}
              onSearch={handleSearch}
            />
          </div>
        )}
      </div>
    </div>
  );
}
