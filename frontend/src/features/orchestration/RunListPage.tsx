import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Plus,
  Play,
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
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { useCampaignStore } from '../../stores/campaignStore';
import type { PipelineSession, RunStatus } from '../../stores/campaignStore';
import { api } from '../../services/api';

const USER_ID = 'default-user';

const STATUS_CONFIG: Record<RunStatus, { label: string; color: string; bgColor: string; icon: typeof Clock }> = {
  idle: { label: 'Idle', color: 'text-zinc-400', bgColor: 'bg-zinc-800', icon: Clock },
  configuring: { label: 'Configuring', color: 'text-yellow-400', bgColor: 'bg-yellow-950/30', icon: Settings },
  queued: { label: 'Queued', color: 'text-blue-400', bgColor: 'bg-blue-950/30', icon: Clock },
  running: { label: 'Running', color: 'text-green-400', bgColor: 'bg-green-950/30', icon: Loader2 },
  paused: { label: 'Paused', color: 'text-amber-400', bgColor: 'bg-amber-950/30', icon: Pause },
  completed: { label: 'Completed', color: 'text-emerald-400', bgColor: 'bg-emerald-950/30', icon: CheckCircle2 },
  error: { label: 'Error', color: 'text-red-400', bgColor: 'bg-red-950/30', icon: XCircle },
};

function formatDuration(ms: number): string {
  const seconds = Math.floor(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const sec = seconds % 60;
  return `${minutes}m ${sec}s`;
}

function formatTimeAgo(timestamp: number): string {
  const ms = Date.now() - timestamp;
  if (ms < 60000) return 'just now';
  if (ms < 3600000) return `${Math.floor(ms / 60000)}m ago`;
  if (ms < 86400000) return `${Math.floor(ms / 3600000)}h ago`;
  return new Date(timestamp).toLocaleDateString();
}

export function RunListPage() {
  const navigate = useNavigate();
  const {
    sessions,
    config,
    selectedSearchTrends,
    selectedYtTrends,
    commercialDuration,
    autopilot,
    activeRubrics,
    addSession,
    removeSession,
    setActiveSession,
    setCampaignConfig,
    setCommercialDuration,
    setSessionId,
    setPipelineStatus,
    setAutopilot,
    setAutoStart,
  } = useCampaignStore();

  const [creating, setCreating] = useState(false);

  const handleNewRun = useCallback(async () => {
    if (creating) return;
    setCreating(true);

    try {
      const initialState: Record<string, any> = {
        brand: config.brand || '',
        target_product: config.target_product || '',
        target_audience: config.target_audience || '',
        key_selling_points: config.key_selling_points || '',
        commercial_duration: commercialDuration,
        autopilot_mode: autopilot,
      };

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

      const session = await api.createSession({ initial_state: initialState });

      const newSession: PipelineSession = {
        id: `session-${Date.now()}`,
        sessionId: session.session_id,
        label: `Run ${sessions.length + 1}`,
        status: 'idle',
        startedAt: Date.now(),
        config: { ...config },
        commercialDuration,
        autopilot,
        parallelStreams: 1,
        searchTrends: [...selectedSearchTrends],
        ytTrends: [...selectedYtTrends],
      };

      addSession(newSession);
      navigate(`/orchestration/${newSession.id}`);
    } catch (err) {
      console.error('Failed to create run:', err);
    } finally {
      setCreating(false);
    }
  }, [creating, config, commercialDuration, autopilot, selectedSearchTrends, selectedYtTrends, sessions.length, addSession, navigate]);

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
            onClick={handleNewRun}
            disabled={creating}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-zinc-700 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-colors"
          >
            {creating ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Plus className="w-4 h-4" />
            )}
            New Run
          </button>
        </div>
      </div>

      {/* Run List */}
      {sessions.length === 0 ? (
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
              disabled={creating}
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors"
            >
              <Plus className="w-4 h-4" />
              Create First Run
            </button>
          </div>
        </div>
      ) : (
        <div className="flex-1 overflow-auto space-y-2">
          {sessions.map((session, index) => {
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
                  <div className="flex items-center gap-2">
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
                  </div>
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
                        <span>{session.commercialDuration}s commercial</span>
                      </>
                    )}
                    {session.currentPhase && (
                      <>
                        <span className="text-zinc-700">|</span>
                        <span className="text-blue-400">{session.currentPhase}</span>
                      </>
                    )}
                  </div>
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
