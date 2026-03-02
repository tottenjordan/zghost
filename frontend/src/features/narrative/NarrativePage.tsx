import { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { ChevronDown } from 'lucide-react';
import { useCampaignStore } from '../../stores/campaignStore';
import type { PipelineSession } from '../../stores/campaignStore';
import { api } from '../../services/api';
import { generateRunLabel } from '../orchestration/RunListPage';
import { cn } from '../../lib/utils';

export function NarrativePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { sessions, mergeBackendSessions } = useCampaignStore();
  const backendLoadedRef = useRef(false);

  const [sessionId, setSessionId] = useState<string | null>(() => {
    return searchParams.get('session') || null;
  });

  // Fetch sessions from backend on mount
  useEffect(() => {
    if (backendLoadedRef.current) return;
    backendLoadedRef.current = true;

    api.listSessions().then((result) => {
      const newSessions: PipelineSession[] = result.sessions.map((s) => {
        const startedAt = s.last_update_time ? s.last_update_time * 1000 : Date.now();
        return {
          id: `backend-${s.session_id}`,
          sessionId: s.session_id,
          label: generateRunLabel(s.session_id, startedAt, s.brand || undefined),
          status: s.status === 'running' || s.status === 'in_progress' ? 'running' as const
            : s.status === 'error' || s.status === 'failed' ? 'error' as const
            : 'completed' as const,
          startedAt,
          createdAt: new Date(startedAt).toISOString(),
          config: {
            brand: s.brand || '',
            target_product: s.target_product || '',
            target_audience: s.target_audience || '',
            key_selling_points: '',
          },
          commercialDuration: (s.commercial_duration as 10 | 15 | 20 | 30) || 30,
          autopilot: s.autopilot_mode || false,
          hasReport: s.has_report,
          hasCommercial: s.has_commercial,
          imageCount: s.image_count,
          videoCount: s.video_count,
          fromBackend: true,
        };
      });
      mergeBackendSessions(newSessions);
    }).catch((err) => console.error('Failed to fetch backend sessions:', err));
  }, [mergeBackendSessions]);

  // Auto-select the most recent session
  useEffect(() => {
    if (sessionId || sessions.length === 0) return;
    const sorted = [...sessions].sort((a, b) => b.startedAt - a.startedAt);
    const withReport = sorted.find((s) => s.hasReport);
    const best = withReport || sorted[0];
    if (best) {
      handleSelectSession(best.sessionId);
    }
  }, [sessions, sessionId]);

  const handleSelectSession = (newSessionId: string) => {
    setSessionId(newSessionId);
    setSearchParams({ session: newSessionId });
  };

  return (
    <div className="flex flex-col h-full gap-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="mb-2 text-3xl font-bold text-zinc-50">
            Narrative Director
          </h1>
          <p className="text-zinc-400">
            Coming soon — review, refine, and iterate on your research report
          </p>
        </div>

        {/* Run selector */}
        {sessions.length > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-zinc-500">Run:</span>
            <div className="relative">
              <select
                value={sessionId || ''}
                onChange={(e) => e.target.value && handleSelectSession(e.target.value)}
                className={cn(
                  'appearance-none pl-3 pr-8 py-1.5 rounded-lg border text-xs',
                  'bg-zinc-900 border-zinc-700 text-zinc-300',
                  'focus:outline-none focus:ring-1 focus:ring-blue-500'
                )}
              >
                <option value="" disabled>Select a run...</option>
                {sessions.map((s) => (
                  <option key={s.sessionId} value={s.sessionId}>
                    {s.label} — {s.config?.brand || 'No brand'} ({s.status})
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3 h-3 text-zinc-500 pointer-events-none" />
            </div>
          </div>
        )}
      </div>

      {/* Placeholder */}
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <p className="text-zinc-500 text-sm">
            {sessionId
              ? `Session selected: ${sessionId}`
              : 'Select a run above to get started'}
          </p>
        </div>
      </div>
    </div>
  );
}
