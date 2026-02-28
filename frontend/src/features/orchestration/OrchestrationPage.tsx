import { useState, useCallback, useEffect, useRef } from 'react';
import { ChevronDown, ChevronUp, FileText, Film, AlertCircle, ArrowLeft } from 'lucide-react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { PipelineGraph } from './PipelineGraph';
import { DAGTimeline } from './DAGTimeline';
import { EventStream } from './EventStream';
import { TaskDrillDown } from './TaskDrillDown';
import { SessionStatePanel } from './SessionStatePanel';
import { AgentChat } from './AgentChat';
import { ResultsGallery } from './ResultsGallery';
import { EvaluationPanel } from './EvaluationPanel';
import { PipelineControls } from './PipelineControls';
import { useOrchestration } from './useOrchestration';
// SessionTabBar replaced by RunListPage
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../components/ui/Tabs';
import { api } from '../../services/api';
import { useCampaignStore } from '../../stores/campaignStore';
import { cn } from '../../lib/utils';
import type { AgentEventType } from '../../types/agents';

const USER_ID = 'default-user';

export function OrchestrationPage() {
  const { runId } = useParams<{ runId: string }>();
  const navigate = useNavigate();
  const [streamUrl, setStreamUrl] = useState<string | null>(null);
  const [startError, setStartError] = useState<string | null>(null);
  const [eventStreamOpen, setEventStreamOpen] = useState(true);
  const [isWaitingForInput, setIsWaitingForInput] = useState(false);
  const [dismissedBanners, setDismissedBanners] = useState<Set<string>>(new Set());
  const [configExpanded, setConfigExpanded] = useState(false);
  const [detailTab, setDetailTab] = useState('chat');
  const originalTitleRef = useRef(document.title);
  const isStartingRef = useRef(false);

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
    autopilot,
    addSession,
    removeSession,
    setActiveSession,
    setSessionId,
    setPipelineStatus,
    setCommercialDuration,
    setAutoStart,
    setAutopilot,
    isReadyToLaunch,
    setCampaignConfig,
    getSessionById,
    updateSession,
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
    if (isStartingRef.current) return;
    isStartingRef.current = true;
    setStartError(null);
    try {
      // Build initial state with campaign config, trends, and commercial duration
      const initialState: Record<string, any> = {
        brand: config.brand || '',
        target_product: config.target_product || '',
        target_audience: config.target_audience || '',
        key_selling_points: config.key_selling_points || '',
        commercial_duration: commercialDuration,
        autopilot_mode: autopilot,
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
        config: { ...config },
        commercialDuration,
        searchTrends: [...selectedSearchTrends],
        ytTrends: [...selectedYtTrends],
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

      const hasTrends = selectedSearchTrends.length > 0 && selectedYtTrends.length > 0;
      const trendSkipNote = hasTrends
        ? ' Campaign metadata and trends are already configured in session state — skip trend-discovery and proceed directly to market research.'
        : '';
      const autopilotNote = autopilot
        ? ' Use auto-select mode for trends, approve all outputs automatically, and proceed through all steps without pausing for user confirmation.'
        : '';
      const pipelineMessage = `Start the full pipeline with ${parallelCount} parallel stream(s), producing a ${commercialDuration}-second commercial.${trendSkipNote}${autopilotNote}${rubricGuidance}`;

      // Set stream URL for live event monitoring (useOrchestration will connect)
      const url = api.getStreamUrl(session.session_id, pipelineMessage, USER_ID);
      setStreamUrl(url);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to start pipeline';
      setStartError(msg);
      setPipelineStatus('error');
    } finally {
      isStartingRef.current = false;
    }
  }, [config, selectedSearchTrends, selectedYtTrends, activeRubrics, commercialDuration, sessions, addSession, setSessionId, setPipelineStatus]);

  // Sync autopilot state with backend session when toggled
  const handleAutopilotChange = useCallback((enabled: boolean) => {
    setAutopilot(enabled);
    if (sessionId) {
      api.updateSessionState(sessionId, { autopilot_mode: enabled }).catch((err) => {
        console.warn('Failed to sync autopilot state:', err);
      });
    }
  }, [sessionId, setAutopilot]);

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

  // Reconnect to running session after page reload / frontend restart
  useEffect(() => {
    if (!sessionId || !isRunning) return;
    // If we have a sessionId + running status but no active stream,
    // try to reconnect
    if (!streamUrl) {
      api.getSessionState(sessionId).then(() => {
        // Session still exists — reconnect SSE stream with a continue message
        const url = api.getStreamUrl(sessionId, 'Continue where you left off.', USER_ID);
        setStreamUrl(url);
      }).catch(() => {
        // Session doesn't exist on the server — reset to idle
        setPipelineStatus('idle');
        setSessionId(null);
      });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Listen for voice-action events to switch tabs
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      if (detail?.action === 'set_detail_tab' && detail?.params?.tab) {
        setDetailTab(detail.params.tab);
      }
    };
    window.addEventListener('voice-action', handler);
    return () => window.removeEventListener('voice-action', handler);
  }, []);

  // Initialize from runId URL param
  useEffect(() => {
    if (!runId) return;
    const session = getSessionById(runId);
    if (session) {
      const idx = sessions.findIndex(s => s.id === runId || s.sessionId === runId);
      if (idx >= 0) {
        setActiveSession(idx);
        setSessionId(session.sessionId);
        if (session.status === 'running') setPipelineStatus('running');
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId]);

  // Auto-start pipeline when navigated from wizard with autoStart flag
  // Bypass isReadyToLaunch() — the wizard already validated before setting autoStart
  useEffect(() => {
    if (autoStart && !isRunning) {
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

  // Auto-navigation detection
  const hasResearchReport = !!sessionState.combined_final_cited_report;
  const hasCommercialVideo = !!(
    sessionState.vid_artifact_keys?.vid_artifact_keys?.length > 0 ||
    (Array.isArray(sessionState.vid_artifact_keys) && sessionState.vid_artifact_keys.length > 0)
  );

  const selectedAgentState = selectedAgent ? status?.agents[selectedAgent] : undefined;
  const selectedAgentEvents = selectedAgent ? getAgentEvents(selectedAgent) : [];
  const { ready: storeReady, missing } = isReadyToLaunch();
  // Suppress "missing trends" when already running with an active session
  const ready = storeReady || (!!sessionId && isRunning);
  const totalTrends = selectedSearchTrends.length + selectedYtTrends.length;

  return (
    <div className="flex flex-col h-full gap-3">
      {/* Input alert banner */}
      {isWaitingForInput && (
        <div
          className="flex items-center gap-3 p-3 bg-amber-950/50 border border-amber-700 rounded-lg animate-pulse cursor-pointer hover:bg-amber-950/70 transition-colors"
          onClick={() => setDetailTab('chat')}
        >
          <AlertCircle className="w-5 h-5 text-amber-400 flex-shrink-0" />
          <span className="text-sm text-amber-300 flex-1">The agent is waiting for your input</span>
          <span className="text-xs text-amber-500">Click to open Chat</span>
        </div>
      )}

      {/* Auto-navigation banners */}
      {hasResearchReport && !dismissedBanners.has('report') && (
        <div className="relative overflow-hidden rounded-lg border border-blue-600 bg-gradient-to-r from-blue-950 via-blue-900 to-blue-950 p-5 shadow-lg">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-blue-600/30 border border-blue-500">
              <FileText className="h-6 w-6 text-blue-300" />
            </div>
            <div className="flex-1">
              <h3 className="text-base font-semibold text-blue-100">Research Report Ready</h3>
              <p className="text-sm text-blue-300/80 mt-0.5">
                Your comprehensive market research report is complete and ready for review
              </p>
            </div>
            <div className="flex items-center gap-3">
              <Link
                to={`/narrative?session=${sessionId}`}
                className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white shadow-md transition-all hover:bg-blue-500 hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-2 focus:ring-offset-zinc-900"
              >
                <FileText className="h-4 w-4" />
                Open in Narrative
              </Link>
              <button
                onClick={() => dismissBanner('report')}
                className="rounded-lg p-2 text-blue-400 transition-colors hover:bg-blue-900/50 hover:text-blue-300"
                aria-label="Dismiss banner"
              >
                ✕
              </button>
            </div>
          </div>
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
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/orchestration')}
              className="p-1.5 rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors"
              title="Back to runs"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <h1 className="text-xl font-bold">
                {sessions[activeSessionIndex]?.label || 'Run Detail'}
              </h1>
              <p className="text-xs text-zinc-500 mt-0.5">Monitor and control the agent pipeline</p>
            </div>
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

      {/* Pipeline Controls */}
      <PipelineControls
        isRunning={isRunning}
        sessionId={sessionId}
        readyToLaunch={ready}
        missingItems={missing}
        commercialDuration={commercialDuration}
        autopilot={autopilot}
        onDurationChange={setCommercialDuration}
        onAutopilotChange={handleAutopilotChange}
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

            <TabsContent value="graph" className="flex-1 h-[500px]">
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
          <Tabs value={detailTab} onValueChange={setDetailTab}>
            <TabsList className="w-full grid grid-cols-6">
              <TabsTrigger value="chat">Chat</TabsTrigger>
              <TabsTrigger value="results">Results</TabsTrigger>
              <TabsTrigger value="evaluation">Eval</TabsTrigger>
              <TabsTrigger value="details">Details</TabsTrigger>
              <TabsTrigger value="config">Config</TabsTrigger>
              <TabsTrigger value="state">State</TabsTrigger>
            </TabsList>

            <TabsContent value="chat" className="flex-1 overflow-hidden">
              <AgentChat
                sessionId={sessionId}
                events={events}
                autopilot={autopilot}
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

            <TabsContent value="config" className="flex-1 overflow-auto p-4">
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  {/* Brand */}
                  <div>
                    <label className="mb-2 block text-xs font-medium text-zinc-400">
                      Brand <span className="text-red-500">*</span>
                    </label>
                    <div className="relative">
                      <input
                        type="text"
                        value={config.brand}
                        onChange={(e) => setCampaignConfig({ ...config, brand: e.target.value })}
                        disabled={isRunning}
                        placeholder="e.g., Google Pixel"
                        className={cn(
                          'flex h-9 w-full rounded-md border px-3 py-2 text-sm',
                          'text-zinc-50 placeholder:text-zinc-500 bg-zinc-900',
                          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500',
                          'disabled:opacity-50 disabled:cursor-not-allowed',
                          config.brand.trim() !== ''
                            ? 'border-zinc-700 border-l-4 border-l-green-500'
                            : 'border-zinc-700'
                        )}
                      />
                      {config.brand.trim() !== '' && (
                        <span className="absolute right-3 top-1/2 -translate-y-1/2 text-green-500 text-xs">
                          ✓
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Product */}
                  <div>
                    <label className="mb-2 block text-xs font-medium text-zinc-400">
                      Product <span className="text-red-500">*</span>
                    </label>
                    <div className="relative">
                      <input
                        type="text"
                        value={config.target_product}
                        onChange={(e) => setCampaignConfig({ ...config, target_product: e.target.value })}
                        disabled={isRunning}
                        placeholder="e.g., Pixel 9 Pro"
                        className={cn(
                          'flex h-9 w-full rounded-md border px-3 py-2 text-sm',
                          'text-zinc-50 placeholder:text-zinc-500 bg-zinc-900',
                          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500',
                          'disabled:opacity-50 disabled:cursor-not-allowed',
                          config.target_product.trim() !== ''
                            ? 'border-zinc-700 border-l-4 border-l-green-500'
                            : 'border-zinc-700'
                        )}
                      />
                      {config.target_product.trim() !== '' && (
                        <span className="absolute right-3 top-1/2 -translate-y-1/2 text-green-500 text-xs">
                          ✓
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Audience */}
                  <div>
                    <label className="mb-2 block text-xs font-medium text-zinc-400">
                      Target Audience
                    </label>
                    <div className="relative">
                      <input
                        type="text"
                        value={config.target_audience}
                        onChange={(e) => setCampaignConfig({ ...config, target_audience: e.target.value })}
                        disabled={isRunning}
                        placeholder="e.g., Tech-savvy millennials"
                        className={cn(
                          'flex h-9 w-full rounded-md border px-3 py-2 text-sm',
                          'text-zinc-50 placeholder:text-zinc-500 bg-zinc-900',
                          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500',
                          'disabled:opacity-50 disabled:cursor-not-allowed',
                          config.target_audience.trim() !== ''
                            ? 'border-zinc-700 border-l-4 border-l-green-500'
                            : 'border-zinc-700'
                        )}
                      />
                      {config.target_audience.trim() !== '' && (
                        <span className="absolute right-3 top-1/2 -translate-y-1/2 text-green-500 text-xs">
                          ✓
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Selling Points */}
                  <div>
                    <label className="mb-2 block text-xs font-medium text-zinc-400">
                      Key Selling Points
                    </label>
                    <div className="relative">
                      <textarea
                        value={config.key_selling_points}
                        onChange={(e) => setCampaignConfig({ ...config, key_selling_points: e.target.value })}
                        disabled={isRunning}
                        placeholder="e.g., AI camera, long battery"
                        rows={3}
                        className={cn(
                          'flex w-full rounded-md border px-3 py-2 text-sm',
                          'text-zinc-50 placeholder:text-zinc-500 bg-zinc-900',
                          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 resize-none',
                          'disabled:opacity-50 disabled:cursor-not-allowed',
                          config.key_selling_points.trim() !== ''
                            ? 'border-zinc-700 border-l-4 border-l-green-500'
                            : 'border-zinc-700'
                        )}
                      />
                      {config.key_selling_points.trim() !== '' && (
                        <span className="absolute right-3 top-2 text-green-500 text-xs">
                          ✓
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Autopilot Toggle */}
                <div className="flex items-center justify-between pt-3 border-t border-zinc-800">
                  <div>
                    <label className="text-xs font-medium text-zinc-400">AI Autopilot Mode</label>
                    <p className="text-xs text-zinc-600 mt-0.5">Auto-approve all agent outputs without pausing</p>
                  </div>
                  <button
                    onClick={() => handleAutopilotChange(!autopilot)}
                    disabled={isRunning}
                    className={cn(
                      'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
                      'disabled:opacity-50 disabled:cursor-not-allowed',
                      autopilot ? 'bg-blue-600' : 'bg-zinc-700'
                    )}
                  >
                    <span className={cn(
                      'inline-block h-4 w-4 transform rounded-full bg-white transition-transform',
                      autopilot ? 'translate-x-6' : 'translate-x-1'
                    )} />
                  </button>
                </div>
              </div>
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
