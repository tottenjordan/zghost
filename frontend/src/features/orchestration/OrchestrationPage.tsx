import { useState, useCallback, useEffect, useRef } from 'react';
import { ChevronDown, ChevronUp, FileText, Film, AlertCircle } from 'lucide-react';
import { Link } from 'react-router-dom';
import { PipelineGraph } from './PipelineGraph';
import { DAGTimeline } from './DAGTimeline';
import { EventStream } from './EventStream';
import { TaskDrillDown } from './TaskDrillDown';
import { ParallelStreamView } from './ParallelStreamView';
import { SessionStatePanel } from './SessionStatePanel';
import { AgentChat } from './AgentChat';
import { ResultsGallery } from './ResultsGallery';
import { EvaluationPanel } from './EvaluationPanel';
import { PipelineControls } from './PipelineControls';
import { SessionTabBar } from './SessionTabBar';
import { useOrchestration } from './useOrchestration';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../components/ui/Tabs';
import { api } from '../../services/api';
import { useCampaignStore } from '../../stores/campaignStore';
import { cn } from '../../lib/utils';
import type { AgentEventType } from '../../types/agents';

const USER_ID = 'default-user';

export function OrchestrationPage() {
  const [streamUrl, setStreamUrl] = useState<string | null>(null);
  const [startError, setStartError] = useState<string | null>(null);
  const [eventStreamOpen, setEventStreamOpen] = useState(true);
  const [isWaitingForInput, setIsWaitingForInput] = useState(false);
  const [dismissedBanners, setDismissedBanners] = useState<Set<string>>(new Set());
  const [configExpanded, setConfigExpanded] = useState(false);
  const originalTitleRef = useRef(document.title);

  const {
    config,
    selectedSearchTrends,
    selectedYtTrends,
    activeRubrics,
    sessions,
    activeSessionIndex,
    sessionId,
    pipelineStatus,
    commercialDuration,
    autoStart,
    addSession,
    removeSession,
    setActiveSession,
    setSessionId,
    setPipelineStatus,
    setCommercialDuration,
    setAutoStart,
    isReadyToLaunch,
  } = useCampaignStore();

  const isRunning = pipelineStatus === 'running';

  const {
    status,
    refetch,
    events,
    getAgentEvents,
    addEvent,
    sessionState,
    changedKeys,
    selectedAgent,
    setSelectedAgent,
    updateFilters,
    clearFilters,
    isPaused,
    togglePause,
  } = useOrchestration(sessionId, streamUrl);

  // Flash browser tab title when input is needed and page not focused
  useEffect(() => {
    if (!isWaitingForInput) {
      document.title = originalTitleRef.current;
      return;
    }

    let flashInterval: ReturnType<typeof setInterval> | null = null;
    let isFlashing = false;

    const handleVisibilityChange = () => {
      if (document.hidden && isWaitingForInput) {
        isFlashing = true;
        let showAlert = true;
        flashInterval = setInterval(() => {
          document.title = showAlert ? '** Input Needed **' : originalTitleRef.current;
          showAlert = !showAlert;
        }, 1000);
      } else {
        if (flashInterval) clearInterval(flashInterval);
        flashInterval = null;
        isFlashing = false;
        document.title = originalTitleRef.current;
      }
    };

    handleVisibilityChange();
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      if (flashInterval) clearInterval(flashInterval);
      document.title = originalTitleRef.current;
    };
  }, [isWaitingForInput]);

  const handleStart = useCallback(async (parallelCount: number) => {
    setStartError(null);
    try {
      // Build initial state with campaign config, trends, and commercial duration
      const initialState: Record<string, any> = {
        brand: config.brand || '',
        target_product: config.target_product || '',
        target_audience: config.target_audience || '',
        key_selling_points: config.key_selling_points || '',
        commercial_duration: commercialDuration,
      };

      // Add selected trends to session state
      if (selectedSearchTrends.length > 0) {
        initialState.target_search_trends = {
          target_search_trends: selectedSearchTrends.map((t) => ({
            trend_title: t.title,
            trend_rank: t.rank,
            trend_refresh_date: '',
          })),
        };
      }

      if (selectedYtTrends.length > 0) {
        initialState.target_yt_trends = {
          target_yt_trends: selectedYtTrends.map((t) => ({
            video_title: t.title,
            video_duration: '',
            video_url: t.videoUrl || '',
          })),
        };
      }

      // Create session with all config preloaded
      const session = await api.createSession({ initial_state: initialState });

      const newSession = {
        id: `session-${Date.now()}`,
        sessionId: session.session_id,
        label: `Run ${sessions.length + 1}`,
        status: 'running' as const,
        startedAt: Date.now(),
      };

      addSession(newSession);
      setSessionId(session.session_id);
      setPipelineStatus('running');

      // Build the pipeline start message with context
      let rubricGuidance = '';
      if (activeRubrics.length > 0) {
        const allCriteria = activeRubrics.flatMap((r) =>
          r.criteria.map((c) => `[${r.name}] ${c.name} (weight: ${c.weight})`)
        );
        rubricGuidance = ` Evaluate outputs against these criteria: ${allCriteria.join(', ')}.`;
      }

      const pipelineMessage = `Start the full pipeline with ${parallelCount} parallel stream(s), producing a ${commercialDuration}-second commercial.${rubricGuidance}`;

      // Set stream URL for live event monitoring (useOrchestration will connect)
      const url = api.getStreamUrl(session.session_id, pipelineMessage, USER_ID);
      setStreamUrl(url);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to start pipeline';
      setStartError(msg);
      setPipelineStatus('error');
    }
  }, [config, selectedSearchTrends, selectedYtTrends, activeRubrics, commercialDuration, sessions, addSession, setSessionId, setPipelineStatus]);

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

  // Route chat messages through the shared EventSource so events
  // reach the timeline, graph, and event stream
  const handleChatMessage = useCallback((message: string) => {
    if (!sessionId) return;
    // Add synthetic user event so chat shows the message immediately
    addEvent({
      type: 'agent_step',
      agentName: 'user',
      data: { parts: [{ text: message }] },
      timestamp: Date.now(),
    });
    const url = api.getStreamUrl(sessionId, message, USER_ID);
    setStreamUrl(url);
  }, [sessionId, addEvent]);

  // Detect stale sessions (server restarted, session lost) and reset state
  useEffect(() => {
    if (!sessionId || !isRunning) return;
    // If we have a sessionId + running status but no active stream,
    // the session is likely stale from a previous server instance
    if (!streamUrl) {
      api.getSessionState(sessionId).catch(() => {
        // Session doesn't exist on the server — reset to idle
        setPipelineStatus('idle');
        setSessionId(null);
      });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Auto-start pipeline when navigated from wizard with autoStart flag
  useEffect(() => {
    if (autoStart && isReadyToLaunch().ready && !isRunning) {
      setAutoStart(false);
      handleStart(1);
    } else if (autoStart) {
      setAutoStart(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const dismissBanner = (key: string) => {
    setDismissedBanners(prev => new Set(prev).add(key));
  };

  // Parallel streams — use substring matching since ADK author field may not exactly match
  const getStreamEvents = (keywords: string[]) =>
    events.filter(e => keywords.some(kw => e.agentName.toLowerCase().includes(kw)));

  const ytEvents = getStreamEvents(['yt_sequential', 'yt_analysis', 'yt_web']);
  const gsEvents = getStreamEvents(['gs_sequential', 'gs_web']);
  const caEvents = getStreamEvents(['ca_sequential', 'campaign_web']);

  const parallelStreams = [
    { id: 'stream-1', name: 'YouTube Research', status: ytEvents.length > 0 ? ('running' as const) : ('pending' as const), progress: Math.min(100, ytEvents.length * 10), currentStage: ytEvents.length > 5 ? 'web_scraping' : ytEvents.length > 0 ? 'planning' : undefined, events: ytEvents },
    { id: 'stream-2', name: 'Google Search', status: gsEvents.length > 0 ? ('running' as const) : ('pending' as const), progress: Math.min(100, gsEvents.length * 10), currentStage: gsEvents.length > 5 ? 'searching' : gsEvents.length > 0 ? 'planning' : undefined, events: gsEvents },
    { id: 'stream-3', name: 'Campaign Research', status: caEvents.length > 0 ? ('running' as const) : ('pending' as const), progress: Math.min(100, caEvents.length * 10), currentStage: caEvents.length > 5 ? 'analysis' : caEvents.length > 0 ? 'planning' : undefined, events: caEvents },
  ].filter(stream => stream.events.length > 0 || sessionId !== null);

  const selectedAgentState = selectedAgent ? status?.agents[selectedAgent] : undefined;
  const selectedAgentEvents = selectedAgent ? getAgentEvents(selectedAgent) : [];
  const { ready, missing } = isReadyToLaunch();
  const totalTrends = selectedSearchTrends.length + selectedYtTrends.length;

  // Auto-navigation detection
  const hasResearchReport = !!sessionState.combined_final_cited_report;
  const hasCommercialVideo = !!(
    sessionState.vid_artifact_keys?.vid_artifact_keys?.length > 0 ||
    (Array.isArray(sessionState.vid_artifact_keys) && sessionState.vid_artifact_keys.length > 0)
  );

  return (
    <div className="flex flex-col h-full gap-3">
      {/* Input alert banner */}
      {isWaitingForInput && (
        <div className="flex items-center gap-3 p-3 bg-amber-950/50 border border-amber-700 rounded-lg animate-pulse">
          <AlertCircle className="w-5 h-5 text-amber-400 flex-shrink-0" />
          <span className="text-sm text-amber-300 flex-1">The agent is waiting for your input</span>
          <span className="text-xs text-amber-500">Check the Chat tab to respond</span>
        </div>
      )}

      {/* Auto-navigation banners */}
      {hasResearchReport && !dismissedBanners.has('report') && (
        <div
          className="flex items-center gap-3 p-3 bg-blue-950/50 border border-blue-700 rounded-lg cursor-pointer hover:bg-blue-950/70 transition-colors"
          onClick={() => dismissBanner('report')}
        >
          <FileText className="w-5 h-5 text-blue-400" />
          <span className="text-sm text-blue-300">Research report is ready</span>
          <Link
            to={`/narrative?session=${sessionId}`}
            className="ml-auto text-xs text-blue-400 underline hover:text-blue-300"
            onClick={(e) => e.stopPropagation()}
          >
            Open in Narrative
          </Link>
        </div>
      )}

      {hasCommercialVideo && !dismissedBanners.has('commercial') && (
        <div
          className="flex items-center gap-3 p-3 bg-green-950/50 border border-green-700 rounded-lg cursor-pointer hover:bg-green-950/70 transition-colors"
          onClick={() => dismissBanner('commercial')}
        >
          <Film className="w-5 h-5 text-green-400" />
          <span className="text-sm text-green-300">Commercial video generated</span>
          <Link
            to="/studio"
            className="ml-auto text-xs text-green-400 underline hover:text-green-300"
            onClick={(e) => e.stopPropagation()}
          >
            Open in AV Studio
          </Link>
        </div>
      )}

      {/* Header + collapsible config panel */}
      <div className="space-y-2">
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
            <span className="px-2 py-0.5 rounded border border-blue-700/50 bg-blue-950/30 text-blue-400">
              {commercialDuration}s commercial
            </span>
            <span className={cn('px-2 py-0.5 rounded border', activeRubrics.length > 0 ? 'border-green-700/50 bg-green-950/30 text-green-400' : 'border-zinc-700/50 bg-zinc-800/50 text-zinc-500')}>
              {activeRubrics.length > 0 ? `${activeRubrics.length} rubric${activeRubrics.length !== 1 ? 's' : ''}` : 'Default rubric'}
            </span>
            <button
              onClick={() => setConfigExpanded(!configExpanded)}
              className="px-2 py-0.5 rounded border border-zinc-700 bg-zinc-800/50 text-zinc-400 hover:text-zinc-300 hover:bg-zinc-700/50 transition-colors"
            >
              {configExpanded ? 'Hide config' : 'Show config'}
            </button>
          </div>
        </div>

        {configExpanded && (
          <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-4 text-sm">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <p className="text-xs font-medium text-zinc-500">Brand</p>
                <p className="text-zinc-200">{config.brand || 'Not set'}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-zinc-500">Product</p>
                <p className="text-zinc-200">{config.target_product || 'Not set'}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-zinc-500">Target Audience</p>
                <p className="text-zinc-200">{config.target_audience || 'Not set'}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-zinc-500">Key Selling Points</p>
                <p className="text-zinc-200">{config.key_selling_points || 'Not set'}</p>
              </div>
            </div>
            <div className="mt-3 grid grid-cols-2 md:grid-cols-3 gap-4">
              <div>
                <p className="text-xs font-medium text-zinc-500">Google Trends ({selectedSearchTrends.length})</p>
                {selectedSearchTrends.length > 0 ? (
                  <ul className="mt-1 space-y-0.5">
                    {selectedSearchTrends.map((t) => (
                      <li key={t.rank} className="text-xs text-zinc-300">&bull; {t.title}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-xs text-zinc-500 mt-1">None</p>
                )}
              </div>
              <div>
                <p className="text-xs font-medium text-zinc-500">YouTube Trends ({selectedYtTrends.length})</p>
                {selectedYtTrends.length > 0 ? (
                  <ul className="mt-1 space-y-0.5">
                    {selectedYtTrends.map((t) => (
                      <li key={t.rank} className="text-xs text-zinc-300">&bull; {t.title}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-xs text-zinc-500 mt-1">None</p>
                )}
              </div>
              <div>
                <p className="text-xs font-medium text-zinc-500">Active Rubrics ({activeRubrics.length})</p>
                {activeRubrics.length > 0 ? (
                  <ul className="mt-1 space-y-0.5">
                    {activeRubrics.map((r) => (
                      <li key={r.id} className="text-xs text-zinc-300">
                        &bull; {r.name} ({r.criteria.length} criteria)
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-xs text-zinc-500 mt-1">Default evaluation</p>
                )}
              </div>
            </div>
            <div className="mt-3 text-xs text-zinc-500">
              Commercial duration: {commercialDuration}s
            </div>
          </div>
        )}
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
        commercialDuration={commercialDuration}
        onDurationChange={setCommercialDuration}
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
          <Tabs defaultValue="chat">
            <TabsList className="w-full grid grid-cols-6">
              <TabsTrigger value="chat">Chat</TabsTrigger>
              <TabsTrigger value="results">Results</TabsTrigger>
              <TabsTrigger value="evaluation">Eval</TabsTrigger>
              <TabsTrigger value="details">Details</TabsTrigger>
              <TabsTrigger value="streams">Streams</TabsTrigger>
              <TabsTrigger value="state">State</TabsTrigger>
            </TabsList>

            <TabsContent value="chat" className="flex-1 overflow-hidden">
              <AgentChat
                sessionId={sessionId}
                events={events}
                onWaitingForInput={setIsWaitingForInput}
                onSendMessage={handleChatMessage}
              />
            </TabsContent>

            <TabsContent value="results" className="flex-1 overflow-auto">
              <ResultsGallery sessionState={sessionState} sessionId={sessionId} />
            </TabsContent>

            <TabsContent value="evaluation" className="flex-1 overflow-auto">
              <EvaluationPanel sessionState={sessionState} rubrics={activeRubrics} />
            </TabsContent>

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
