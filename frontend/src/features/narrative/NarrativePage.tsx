import { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { ChevronDown, FileText, Loader2, X, GitMerge, AlertCircle } from 'lucide-react';
import { NarrativeChat } from './NarrativeChat';
import { useNarrative } from './useNarrative';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../components/ui/Tabs';
import { Button } from '../../components/ui/Button';
import { Markdown } from '../../components/ui/Markdown';
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
  const [draftPdfError, setDraftPdfError] = useState(false);
  const [finalPdfError, setFinalPdfError] = useState(false);
  const [activeTab, setActiveTab] = useState('draft');

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
    if (best) handleSelectSession(best.sessionId);
  }, [sessions, sessionId]);

  const handleSelectSession = (newSessionId: string) => {
    setSessionId(newSessionId);
    setSearchParams({ session: newSessionId });
  };

  const {
    messages,
    isStreaming,
    sessionState,
    draftPdfUrl,
    finalPdfUrl,
    pendingChanges,
    isCommitting,
    sendMessage,
    removePendingChange,
    commitChanges,
  } = useNarrative(sessionId);

  const hasDraftPdf = !!draftPdfUrl;
  const hasFinalPdf = !!finalPdfUrl;

  // Auto-switch to final tab when final PDF becomes available
  useEffect(() => {
    if (hasFinalPdf) setActiveTab('final');
  }, [hasFinalPdf]);

  // Auto-switch to pending tab when first change is added
  useEffect(() => {
    if (pendingChanges.length === 1) setActiveTab('pending');
  }, [pendingChanges.length]);

  // Reset PDF errors when URLs change
  useEffect(() => { setDraftPdfError(false); }, [draftPdfUrl]);
  useEffect(() => { setFinalPdfError(false); }, [finalPdfUrl]);

  return (
    <div className="flex flex-col h-full gap-4">
      {/* Header */}
      <div className="flex items-start justify-between flex-shrink-0">
        <div>
          <h1 className="mb-1 text-2xl font-bold text-zinc-50">Narrative Director</h1>
          <p className="text-xs text-zinc-400">
            Review the draft report, request changes via chat, then commit to generate a final PDF
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

      {/* Two-panel layout */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-4 min-h-0 overflow-hidden">
        {/* Left: Chat */}
        <div className="flex flex-col min-h-0 overflow-hidden">
          <NarrativeChat
            messages={messages}
            isStreaming={isStreaming}
            onSendMessage={sendMessage}
            sources={sessionState?.sources}
          />
        </div>

        {/* Right: Draft / Final / Pending Changes tabs */}
        <div className="flex flex-col min-h-0 overflow-hidden border border-zinc-800 rounded-lg bg-zinc-900/50">
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="w-full flex flex-shrink-0">
              <TabsTrigger value="draft">
                Draft Report
              </TabsTrigger>
              <TabsTrigger value="final">
                Final Report
                {hasFinalPdf && (
                  <span className="ml-1.5 w-1.5 h-1.5 rounded-full bg-green-500 inline-block" />
                )}
              </TabsTrigger>
              <TabsTrigger value="pending">
                Pending
                {pendingChanges.length > 0 && (
                  <span className="ml-1.5 px-1.5 py-0.5 text-[10px] bg-amber-600 text-white rounded-full leading-none">
                    {pendingChanges.length}
                  </span>
                )}
              </TabsTrigger>
            </TabsList>

            {/* Draft Report tab */}
            <TabsContent value="draft" className="flex-1 min-h-0 overflow-hidden mt-0">
              {hasDraftPdf && !draftPdfError ? (
                <iframe
                  src={draftPdfUrl}
                  className="w-full h-full min-h-[400px]"
                  title="Draft Research Report PDF"
                  style={{ border: 'none' }}
                  onError={() => setDraftPdfError(true)}
                />
              ) : draftPdfError ? (
                <div className="p-4 overflow-y-auto h-full">
                  <div className="flex items-center gap-2 p-3 mb-4 bg-amber-950/30 border border-amber-800/50 rounded-lg">
                    <AlertCircle className="w-4 h-4 text-amber-400 flex-shrink-0" />
                    <p className="text-sm text-amber-300">Draft PDF failed to load. Showing markdown instead.</p>
                  </div>
                  <div className="prose prose-invert max-w-none">
                    <Markdown
                      content={
                        (typeof sessionState?.final_report_with_citations === 'string'
                          ? sessionState.final_report_with_citations
                          : typeof sessionState?.combined_final_cited_report === 'string'
                            ? sessionState.combined_final_cited_report
                            : null) || 'Report content not available.'
                      }
                      sources={sessionState?.sources}
                    />
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-full p-8 text-center">
                  <FileText className="w-10 h-10 text-zinc-600 mb-3" />
                  <p className="text-sm text-zinc-500">No draft PDF available</p>
                  <p className="text-xs text-zinc-600 mt-1">Run the pipeline to generate a draft research report</p>
                </div>
              )}
            </TabsContent>

            {/* Final Report tab */}
            <TabsContent value="final" className="flex-1 min-h-0 overflow-hidden mt-0">
              {hasFinalPdf && !finalPdfError ? (
                <iframe
                  src={finalPdfUrl}
                  className="w-full h-full min-h-[400px]"
                  title="Final Research Report PDF"
                  style={{ border: 'none' }}
                  onError={() => setFinalPdfError(true)}
                />
              ) : finalPdfError ? (
                <div className="p-4 overflow-y-auto h-full">
                  <div className="flex items-center gap-2 p-3 mb-4 bg-amber-950/30 border border-amber-800/50 rounded-lg">
                    <AlertCircle className="w-4 h-4 text-amber-400 flex-shrink-0" />
                    <p className="text-sm text-amber-300">Final PDF failed to load.</p>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-full p-8 text-center">
                  <FileText className="w-10 h-10 text-zinc-600 mb-3" />
                  <p className="text-sm text-zinc-500">No final report yet</p>
                  <p className="text-xs text-zinc-600 mt-1">
                    Add changes via chat, then commit to generate the final PDF
                  </p>
                </div>
              )}
            </TabsContent>

            {/* Pending Changes tab */}
            <TabsContent value="pending" className="flex-1 min-h-0 overflow-hidden mt-0">
              <div className="flex flex-col h-full">
                {/* Changes list */}
                <div className="flex-1 overflow-y-auto p-4 space-y-2">
                  {pendingChanges.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full text-center">
                      <GitMerge className="w-10 h-10 text-zinc-600 mb-3" />
                      <p className="text-sm text-zinc-500">No pending changes</p>
                      <p className="text-xs text-zinc-600 mt-1">
                        Use the chat to describe changes you want (e.g. "make it more humorous")
                      </p>
                    </div>
                  ) : (
                    pendingChanges.map((change, i) => (
                      <div
                        key={change.id}
                        className="flex items-start gap-3 p-3 rounded-lg border border-zinc-700/50 bg-zinc-800/50"
                      >
                        <span className="flex-shrink-0 w-5 h-5 rounded-full bg-amber-600/20 border border-amber-600/40 flex items-center justify-center text-[10px] text-amber-400 font-medium mt-0.5">
                          {i + 1}
                        </span>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-zinc-200">{change.direction}</p>
                          <p className="text-[10px] text-zinc-500 mt-1">
                            {new Date(change.addedAt).toLocaleTimeString()}
                          </p>
                        </div>
                        <button
                          onClick={() => removePendingChange(change.id)}
                          className="flex-shrink-0 p-1 rounded hover:bg-zinc-700 text-zinc-500 hover:text-zinc-300 transition-colors"
                          title="Remove change"
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ))
                  )}
                </div>

                {/* Commit button */}
                {pendingChanges.length > 0 && (
                  <div className="flex-shrink-0 p-4 border-t border-zinc-800">
                    <Button
                      onClick={commitChanges}
                      variant="primary"
                      size="md"
                      className="w-full flex items-center justify-center gap-2"
                      disabled={isCommitting}
                    >
                      {isCommitting ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <GitMerge className="w-4 h-4" />
                      )}
                      {isCommitting
                        ? 'Merging changes & generating PDF...'
                        : `Commit Draft Changes (${pendingChanges.length})`}
                    </Button>
                    <p className="text-[10px] text-zinc-500 mt-2 text-center">
                      Merges all changes into the original report via LLM and generates a new final PDF
                    </p>
                  </div>
                )}
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  );
}
