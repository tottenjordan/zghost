import { useState, useCallback, useMemo, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Plus,
  Pause,
  Trash2,
  Copy,
  Settings,
  Clock,
  CheckCircle2,
  XCircle,
  Loader2,
  ChevronRight,
  Zap,
  Bot,
  ArrowUpDown,
  Filter,
  FileText,
  Film,
  Image,
  RefreshCw,
  Database,
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { useCampaignStore } from '../../stores/campaignStore';
import type { PipelineSession, RunStatus } from '../../stores/campaignStore';
import { api } from '../../services/api';
import type { SessionSummary } from '../../services/api';

const STATUS_CONFIG: Record<RunStatus, { label: string; color: string; bgColor: string; icon: typeof Clock }> = {
  idle: { label: 'Idle', color: 'text-zinc-400', bgColor: 'bg-zinc-800', icon: Clock },
  configuring: { label: 'Configuring', color: 'text-yellow-400', bgColor: 'bg-yellow-950/30', icon: Settings },
  queued: { label: 'Queued', color: 'text-blue-400', bgColor: 'bg-blue-950/30', icon: Clock },
  running: { label: 'Running', color: 'text-green-400', bgColor: 'bg-green-950/30', icon: Loader2 },
  paused: { label: 'Paused', color: 'text-amber-400', bgColor: 'bg-amber-950/30', icon: Pause },
  completed: { label: 'Completed', color: 'text-emerald-400', bgColor: 'bg-emerald-950/30', icon: CheckCircle2 },
  error: { label: 'Error', color: 'text-red-400', bgColor: 'bg-red-950/30', icon: XCircle },
};

/** Map backend status strings to RunStatus */
function mapBackendStatus(status?: string | null): RunStatus {
  if (!status) return 'idle';
  if (status === 'completed') return 'completed';
  // Intermediate *_done statuses are completed phases, not actively running
  if (status.endsWith('_done')) return 'completed';
  if (status === 'trends_selected') return 'configuring';
  if (status === 'running' || status === 'in_progress') return 'running';
  return 'idle';
}

function formatDuration(ms: number): string {
  const seconds = Math.floor(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const sec = seconds % 60;
  if (minutes < 60) return `${minutes}m ${sec}s`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ${minutes % 60}m`;
}

function formatTimestamp(epochSeconds: number): string {
  if (!epochSeconds) return '';
  const d = new Date(epochSeconds * 1000);
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatTimeAgo(timestamp: number): string {
  const ms = Date.now() - timestamp;
  if (ms < 60000) return 'just now';
  if (ms < 3600000) return `${Math.floor(ms / 60000)}m ago`;
  if (ms < 86400000) return `${Math.floor(ms / 3600000)}h ago`;
  return new Date(timestamp).toLocaleDateString();
}

/** Generate a label from session ID and timestamp */
export function generateRunLabel(sessionId: string, timestamp: number, brand?: string): string {
  const shortId = sessionId.slice(0, 8);
  const d = new Date(timestamp);
  const timeStr = d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
  const dateStr = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  const prefix = brand || 'Run';
  return `${prefix} ${dateStr} ${timeStr} [${shortId}]`;
}

export function RunListPage() {
  const navigate = useNavigate();
  const {
    sessions,
    config,
    maxConcurrentRuns,
    queuedRuns,
    setMaxConcurrentRuns,
    enqueueRun,
    addSession,
    mergeBackendSessions,
    removeSession,
    setActiveSession,
    setCampaignConfig,
    setCommercialDuration,
    setSessionId,
    setPipelineStatus,
  } = useCampaignStore();

  const [loadingBackend, setLoadingBackend] = useState(false);
  const [backendLoaded, setBackendLoaded] = useState(false);

  type SortField = 'time' | 'name' | 'status' | 'duration';
  type SortDir = 'asc' | 'desc';
  const [sortField, setSortField] = useState<SortField>('time');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const [statusFilter, setStatusFilter] = useState<RunStatus | 'all'>('all');
  const [copiedSessionId, setCopiedSessionId] = useState<string | null>(null);

  // Fetch sessions from backend on mount
  useEffect(() => {
    if (backendLoaded) return;

    const fetchBackendSessions = async () => {
      setLoadingBackend(true);
      try {
        const result = await api.listSessions();

        // Build all new sessions in one pass, then merge atomically
        const newSessions: PipelineSession[] = result.sessions.map((summary) => {
          const backendStatus = mapBackendStatus(summary.status);
          const startedAt = summary.last_update_time
            ? summary.last_update_time * 1000
            : Date.now();

          return {
            id: `backend-${summary.session_id}`,
            sessionId: summary.session_id,
            label: generateRunLabel(
              summary.session_id,
              startedAt,
              summary.brand || undefined
            ),
            status: backendStatus,
            startedAt,
            createdAt: new Date(startedAt).toISOString(),
            config: {
              brand: summary.brand || '',
              target_product: summary.target_product || '',
              target_audience: summary.target_audience || '',
              key_selling_points: '',
            },
            commercialDuration: (summary.commercial_duration as 10 | 15 | 30) || 30,
            autopilot: summary.autopilot_mode || false,
            hasReport: summary.has_report,
            hasCommercial: summary.has_commercial,
            imageCount: summary.image_count,
            videoCount: summary.video_count,
            fromBackend: true,
          };
        });

        // Single atomic merge — dedup handled inside the store
        mergeBackendSessions(newSessions);
      } catch (err) {
        console.error('Failed to fetch backend sessions:', err);
      } finally {
        setLoadingBackend(false);
        setBackendLoaded(true);
      }
    };

    fetchBackendSessions();
  }, [backendLoaded]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleRefreshSessions = useCallback(() => {
    setBackendLoaded(false); // triggers re-fetch
  }, []);

  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDir(field === 'time' ? 'desc' : 'asc');
    }
  };

  const sortedSessions = useMemo(() => {
    let filtered = statusFilter === 'all'
      ? [...sessions]
      : sessions.filter((s) => s.status === statusFilter);

    filtered.sort((a, b) => {
      let cmp = 0;
      switch (sortField) {
        case 'time':
          cmp = a.startedAt - b.startedAt;
          break;
        case 'name':
          cmp = a.label.localeCompare(b.label);
          break;
        case 'status':
          cmp = a.status.localeCompare(b.status);
          break;
        case 'duration': {
          const dA = (a.completedAt || Date.now()) - a.startedAt;
          const dB = (b.completedAt || Date.now()) - b.startedAt;
          cmp = dA - dB;
          break;
        }
      }
      return sortDir === 'asc' ? cmp : -cmp;
    });

    return filtered;
  }, [sessions, sortField, sortDir, statusFilter]);

  const handleNewRun = useCallback(() => {
    navigate('/trends');
  }, [navigate]);

  const handleOpenRun = useCallback((session: PipelineSession, index: number) => {
    setActiveSession(index);
    setSessionId(session.sessionId);
    setPipelineStatus(session.status === 'idle' ? 'idle' : session.status);
    navigate(`/orchestration/${session.id}`);
  }, [setActiveSession, setSessionId, setPipelineStatus, navigate]);

  const handleDuplicate = useCallback((session: PipelineSession) => {
    if (session.config) setCampaignConfig(session.config);
    if (session.commercialDuration) setCommercialDuration(session.commercialDuration);
    handleNewRun();
  }, [setCampaignConfig, setCommercialDuration, handleNewRun]);

  const handleDelete = useCallback((session: PipelineSession) => {
    if (window.confirm(`Delete "${session.label}"? This cannot be undone.`)) {
      removeSession(session.sessionId);
    }
  }, [removeSession]);

  const handleCopySessionId = useCallback((sessionId: string) => {
    navigator.clipboard.writeText(sessionId);
    setCopiedSessionId(sessionId);
    setTimeout(() => setCopiedSessionId(null), 2000);
  }, []);

  const runningCount = sessions.filter(s => s.status === 'running').length;
  const completedCount = sessions.filter(s => s.status === 'completed').length;
  const errorCount = sessions.filter(s => s.status === 'error').length;

  return (
    <div className="flex flex-col h-full gap-4 p-1">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-zinc-100">Pipeline Runs</h1>
          <p className="text-xs text-zinc-500 mt-0.5">
            Manage and monitor your marketing pipeline executions
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Summary badges */}
          <div className="flex items-center gap-2 text-xs">
            {sessions.length > 0 && (
              <span className="px-2 py-0.5 rounded bg-zinc-800 text-zinc-400 border border-zinc-700">
                {sessions.length} total
              </span>
            )}
            {runningCount > 0 && (
              <span className="px-2 py-0.5 rounded bg-green-950/30 text-green-400 border border-green-800/50">
                {runningCount} running
              </span>
            )}
            {completedCount > 0 && (
              <span className="px-2 py-0.5 rounded bg-emerald-950/30 text-emerald-400 border border-emerald-800/50">
                {completedCount} done
              </span>
            )}
            {errorCount > 0 && (
              <span className="px-2 py-0.5 rounded bg-red-950/30 text-red-400 border border-red-800/50">
                {errorCount} errors
              </span>
            )}
          </div>
          <button
            onClick={handleRefreshSessions}
            disabled={loadingBackend}
            className="p-2 rounded-lg border border-zinc-700 hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors disabled:opacity-50"
            title="Refresh from Vertex Session Service"
          >
            <RefreshCw className={cn('w-4 h-4', loadingBackend && 'animate-spin')} />
          </button>
          <div className="flex items-center gap-2 border-l border-zinc-700 pl-3">
            <label htmlFor="max-concurrent" className="text-xs text-zinc-400">
              Max concurrent:
            </label>
            <div className="flex items-center gap-1">
              {[1, 2, 3, 4].map((n) => (
                <button
                  key={n}
                  onClick={() => setMaxConcurrentRuns(n)}
                  className={cn(
                    'px-2.5 py-1 text-xs font-medium rounded transition-colors',
                    maxConcurrentRuns === n
                      ? 'bg-blue-600 text-white'
                      : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700 hover:text-zinc-300'
                  )}
                >
                  {n}
                </button>
              ))}
            </div>
          </div>
          <button
            onClick={handleNewRun}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors"
          >
            <Plus className="w-4 h-4" />
            New Run
          </button>
        </div>
      </div>

      {/* Sort & Filter Bar */}
      {sessions.length > 1 && (
        <div className="flex items-center gap-3 flex-wrap">
          {/* Sort buttons */}
          <div className="flex items-center gap-1">
            <ArrowUpDown className="w-3 h-3 text-zinc-500 mr-1" />
            {(['time', 'name', 'status', 'duration'] as SortField[]).map((f) => (
              <button
                key={f}
                onClick={() => toggleSort(f)}
                className={cn(
                  'px-2 py-0.5 rounded text-xs transition-colors',
                  sortField === f
                    ? 'bg-zinc-700 text-zinc-200 font-medium'
                    : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800'
                )}
              >
                {f === 'time' ? 'Time' : f === 'name' ? 'Name' : f === 'status' ? 'Status' : 'Duration'}
                {sortField === f && (
                  <span className="ml-0.5">{sortDir === 'asc' ? '\u2191' : '\u2193'}</span>
                )}
              </button>
            ))}
          </div>

          <div className="w-px h-4 bg-zinc-700" />

          {/* Status filter */}
          <div className="flex items-center gap-1">
            <Filter className="w-3 h-3 text-zinc-500 mr-1" />
            <button
              onClick={() => setStatusFilter('all')}
              className={cn(
                'px-2 py-0.5 rounded text-xs transition-colors',
                statusFilter === 'all'
                  ? 'bg-zinc-700 text-zinc-200 font-medium'
                  : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800'
              )}
            >
              All
            </button>
            {(['running', 'completed', 'error', 'idle'] as RunStatus[]).map((s) => {
              const count = sessions.filter((sess) => sess.status === s).length;
              if (count === 0) return null;
              const cfg = STATUS_CONFIG[s];
              return (
                <button
                  key={s}
                  onClick={() => setStatusFilter(statusFilter === s ? 'all' : s)}
                  className={cn(
                    'px-2 py-0.5 rounded text-xs transition-colors',
                    statusFilter === s
                      ? `${cfg.bgColor} ${cfg.color} font-medium`
                      : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800'
                  )}
                >
                  {cfg.label} ({count})
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Loading indicator */}
      {loadingBackend && sessions.length === 0 && (
        <div className="flex items-center justify-center py-8 gap-2 text-zinc-500 text-sm">
          <Loader2 className="w-4 h-4 animate-spin" />
          Loading sessions from Vertex...
        </div>
      )}

      {/* Run List */}
      {!loadingBackend && sessions.length === 0 ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center space-y-4">
            <div className="mx-auto w-16 h-16 rounded-full bg-zinc-800 flex items-center justify-center">
              <Bot className="w-8 h-8 text-zinc-500" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-zinc-300">No pipeline runs yet</h2>
              <p className="text-sm text-zinc-500 mt-1">
                Configure your campaign on the Trends page, then create a new run
              </p>
            </div>
            <button
              onClick={handleNewRun}
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors"
            >
              <Plus className="w-4 h-4" />
              Create First Run
            </button>
          </div>
        </div>
      ) : (
        <div className="flex-1 overflow-auto space-y-2">
          {sortedSessions.map((session) => {
            const index = sessions.findIndex((s) => s.id === session.id);
            const statusConfig = STATUS_CONFIG[session.status] || STATUS_CONFIG.idle;
            const StatusIcon = statusConfig.icon;
            const isRunning = session.status === 'running';
            const canDelete = session.status !== 'running';
            const duration = session.completedAt
              ? formatDuration(session.completedAt - session.startedAt)
              : isRunning
                ? formatDuration(Date.now() - session.startedAt)
                : null;

            return (
              <div
                key={session.id}
                onClick={() => handleOpenRun(session, index)}
                className={cn(
                  'group relative flex items-center gap-4 p-4 rounded-lg border cursor-pointer transition-all',
                  'hover:bg-zinc-800/50 hover:border-zinc-600',
                  isRunning
                    ? 'border-green-800/50 bg-green-950/10'
                    : 'border-zinc-800 bg-zinc-900/30'
                )}
              >
                {/* Status indicator */}
                <div className={cn(
                  'flex items-center justify-center w-10 h-10 rounded-lg flex-shrink-0',
                  statusConfig.bgColor, 'border',
                  isRunning ? 'border-green-700/50' : 'border-zinc-700/50'
                )}>
                  <StatusIcon className={cn(
                    'w-5 h-5',
                    statusConfig.color,
                    isRunning && 'animate-spin'
                  )} />
                </div>

                {/* Main info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="text-sm font-semibold text-zinc-200 truncate">
                      {session.label}
                    </h3>
                    <span className={cn(
                      'px-1.5 py-0.5 text-[10px] font-medium rounded',
                      statusConfig.bgColor, statusConfig.color,
                      'border',
                      isRunning ? 'border-green-700/50' : 'border-zinc-700/30'
                    )}>
                      {statusConfig.label}
                    </span>
                    {session.autopilot && (
                      <span className="flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] font-medium rounded bg-blue-950/30 text-blue-400 border border-blue-800/30">
                        <Zap className="w-2.5 h-2.5" />
                        Autopilot
                      </span>
                    )}
                    {session.fromBackend && (
                      <span className="flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] font-medium rounded bg-purple-950/30 text-purple-400 border border-purple-800/30">
                        <Database className="w-2.5 h-2.5" />
                        Vertex
                      </span>
                    )}
                  </div>

                  {/* Metadata row */}
                  <div className="flex items-center gap-3 mt-1 text-xs text-zinc-500">
                    {session.config?.brand && (
                      <span>{session.config.brand}</span>
                    )}
                    {session.config?.target_product && (
                      <>
                        <span className="text-zinc-700">/</span>
                        <span>{session.config.target_product}</span>
                      </>
                    )}
                    {session.commercialDuration && (
                      <>
                        <span className="text-zinc-700">|</span>
                        <span>{session.commercialDuration}s</span>
                      </>
                    )}
                    {session.currentPhase && (
                      <>
                        <span className="text-zinc-700">|</span>
                        <span className="text-blue-400">{session.currentPhase}</span>
                      </>
                    )}
                    {session.status === 'queued' && (() => {
                      const position = queuedRuns.indexOf(session.sessionId);
                      if (position >= 0) {
                        return (
                          <>
                            <span className="text-zinc-700">|</span>
                            <span className="text-blue-400">Position #{position + 1} in queue</span>
                          </>
                        );
                      }
                      return null;
                    })()}
                  </div>

                  {/* Session ID + timestamp row */}
                  <div className="flex items-center gap-3 mt-0.5 text-[10px] text-zinc-600 font-mono">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleCopySessionId(session.sessionId);
                      }}
                      className="flex items-center gap-1 hover:text-zinc-400 transition-colors group"
                      title={`${session.sessionId}${(session.config as any)?.agent_engine_id ? `\nAgent Engine ID: ${(session.config as any).agent_engine_id}` : ''}`}
                    >
                      <span>{session.sessionId.slice(0, 12)}...</span>
                      {copiedSessionId === session.sessionId ? (
                        <span className="text-green-500 text-[9px]">Copied!</span>
                      ) : (
                        <Copy className="w-2.5 h-2.5 opacity-0 group-hover:opacity-100 transition-opacity" />
                      )}
                    </button>
                    <span>
                      {session.createdAt
                        ? new Date(session.createdAt).toLocaleString('en-US', {
                            month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
                          })
                        : new Date(session.startedAt).toLocaleString('en-US', {
                            month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
                          })}
                    </span>
                  </div>

                  {/* Artifact tags */}
                  {(session.hasReport || session.hasCommercial || (session.imageCount && session.imageCount > 0) || (session.videoCount && session.videoCount > 0)) && (
                    <div className="flex items-center gap-1.5 mt-1.5">
                      {session.hasReport && (
                        <span className="flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] rounded bg-blue-950/20 text-blue-400 border border-blue-800/20">
                          <FileText className="w-2.5 h-2.5" />
                          Report
                        </span>
                      )}
                      {session.imageCount && session.imageCount > 0 ? (
                        <span className="flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] rounded bg-cyan-950/20 text-cyan-400 border border-cyan-800/20">
                          <Image className="w-2.5 h-2.5" />
                          {session.imageCount} images
                        </span>
                      ) : null}
                      {session.videoCount && session.videoCount > 0 ? (
                        <span className="flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] rounded bg-green-950/20 text-green-400 border border-green-800/20">
                          <Film className="w-2.5 h-2.5" />
                          {session.videoCount} videos
                        </span>
                      ) : null}
                      {session.hasCommercial && (
                        <span className="flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] rounded bg-amber-950/20 text-amber-400 border border-amber-800/20">
                          <Film className="w-2.5 h-2.5" />
                          Commercial
                        </span>
                      )}
                    </div>
                  )}
                </div>

                {/* Timing */}
                <div className="flex flex-col items-end gap-1 flex-shrink-0">
                  {duration && (
                    <span className="text-xs font-mono text-zinc-400">{duration}</span>
                  )}
                  <span className="text-[10px] text-zinc-600">
                    {formatTimeAgo(session.startedAt)}
                  </span>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0">
                  <button
                    onClick={(e) => { e.stopPropagation(); handleDuplicate(session); }}
                    className="p-1.5 rounded hover:bg-zinc-700 text-zinc-500 hover:text-zinc-300 transition-colors"
                    title="Duplicate run"
                  >
                    <Copy className="w-3.5 h-3.5" />
                  </button>
                  {canDelete && (
                    <button
                      onClick={(e) => { e.stopPropagation(); handleDelete(session); }}
                      className="p-1.5 rounded hover:bg-red-950/50 text-zinc-500 hover:text-red-400 transition-colors"
                      title="Delete run"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>

                {/* Chevron */}
                <ChevronRight className="w-4 h-4 text-zinc-600 group-hover:text-zinc-400 transition-colors flex-shrink-0" />
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
