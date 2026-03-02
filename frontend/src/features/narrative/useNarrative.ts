import { useState, useCallback, useEffect, useRef } from 'react';
import { api, gcsToProxyUrl } from '../../services/api';
import type { SessionState } from '../../types/session';
import type { Message, NarrativeData } from './types';

export interface PendingChange {
  id: string;
  direction: string;
  addedAt: number;
}

const GCS_BUCKET = import.meta.env.VITE_GCS_BUCKET || 'zghost-media-center';

export function useNarrative(sessionId: string | null) {
  const [narrativeData, setNarrativeData] = useState<NarrativeData>({
    messages: [],
    scenes: [],
    narrativeArc: undefined,
    isStreaming: false,
  });
  const [sessionState, setSessionState] = useState<SessionState>({});
  const [draftPdfUrl, setDraftPdfUrl] = useState<string | null>(null);
  const [finalPdfUrl, setFinalPdfUrl] = useState<string | null>(null);
  const [pendingChanges, setPendingChanges] = useState<PendingChange[]>([]);
  const [isCommitting, setIsCommitting] = useState(false);

  // Reset state when session changes
  useEffect(() => {
    setNarrativeData({ messages: [], scenes: [], narrativeArc: undefined, isStreaming: false });
    setPendingChanges([]);
    setDraftPdfUrl(null);
    setFinalPdfUrl(null);
  }, [sessionId]);

  const draftGeneratedRef = useRef(false);

  // Auto-load session state
  useEffect(() => {
    if (!sessionId) return;
    draftGeneratedRef.current = false;

    const loadSessionData = () => {
      api.getSessionState(sessionId)
        .then(async (result) => {
          setSessionState(result.state);

          const draftPdf = result.state?.draft_pdf_url;
          if (draftPdf) {
            setDraftPdfUrl(gcsToProxyUrl(draftPdf));
          } else if (!draftGeneratedRef.current) {
            // Probe well-known GCS path where the pipeline stores the draft PDF
            const gcsFolder = result.state?.gcs_folder;
            if (gcsFolder) {
              const wellKnownUri = `gs://${GCS_BUCKET}/${gcsFolder}/draft_research_report_with_citations.pdf`;
              const proxyUrl = gcsToProxyUrl(wellKnownUri);
              try {
                const probe = await fetch(proxyUrl);
                if (probe.ok) {
                  // PDF exists at well-known path — use it directly
                  setDraftPdfUrl(proxyUrl);
                  draftGeneratedRef.current = true;
                } else {
                  throw new Error('Not found');
                }
              } catch {
                // Well-known path doesn't exist — fall back to auto-generation from markdown
                if (result.state?.final_report_with_citations || result.state?.combined_final_cited_report) {
                  draftGeneratedRef.current = true;
                  api.generatePdf(sessionId, undefined, undefined, 'draft')
                    .then((pdfResult) => {
                      setDraftPdfUrl(gcsToProxyUrl(pdfResult.gcs_uri));
                    })
                    .catch((err) => console.error('Failed to auto-generate draft PDF:', err));
                }
              }
            } else if (result.state?.final_report_with_citations || result.state?.combined_final_cited_report) {
              // No gcs_folder — skip probe, go straight to auto-generation
              draftGeneratedRef.current = true;
              api.generatePdf(sessionId, undefined, undefined, 'draft')
                .then((pdfResult) => {
                  setDraftPdfUrl(gcsToProxyUrl(pdfResult.gcs_uri));
                })
                .catch((err) => console.error('Failed to auto-generate draft PDF:', err));
            }
          }

          const finalPdf = result.state?.final_pdf_url;
          if (finalPdf) setFinalPdfUrl(gcsToProxyUrl(finalPdf));
        })
        .catch((err) => console.error('Failed to load session data:', err));
    };

    loadSessionData();
    const intervalId = setInterval(loadSessionData, 5000);
    return () => clearInterval(intervalId);
  }, [sessionId]);

  // Chat: add direction to pending changes (no LLM call)
  const sendMessage = useCallback(
    (content: string) => {
      const userMessage: Message = {
        id: `msg_${Date.now()}`,
        role: 'user',
        content,
        timestamp: Date.now(),
      };

      const change: PendingChange = {
        id: `change_${Date.now()}`,
        direction: content,
        addedAt: Date.now(),
      };

      setPendingChanges((prev) => [...prev, change]);

      const ack: Message = {
        id: `msg_${Date.now()}_ack`,
        role: 'assistant',
        content: `Added to pending changes: **"${content}"**. Switch to the **Pending Changes** tab to review, then click **Commit Draft Changes** when ready.`,
        timestamp: Date.now(),
      };

      setNarrativeData((prev) => ({
        ...prev,
        messages: [...prev.messages, userMessage, ack],
      }));
    },
    []
  );

  // Remove a pending change
  const removePendingChange = useCallback((changeId: string) => {
    setPendingChanges((prev) => prev.filter((c) => c.id !== changeId));
  }, []);

  // Commit: merge all pending directions via LLM → generate final PDF
  const commitChanges = useCallback(async () => {
    if (!sessionId || pendingChanges.length === 0) return null;
    setIsCommitting(true);

    const statusMsg: Message = {
      id: `msg_${Date.now()}_commit`,
      role: 'assistant',
      content: `Committing ${pendingChanges.length} change${pendingChanges.length > 1 ? 's' : ''}... merging via LLM and generating final PDF.`,
      timestamp: Date.now(),
    };

    setNarrativeData((prev) => ({
      ...prev,
      messages: [...prev.messages, statusMsg],
    }));

    try {
      const directions = pendingChanges.map((c) => c.direction);
      const result = await api.commitChanges(sessionId, directions);

      setFinalPdfUrl(gcsToProxyUrl(result.gcs_uri));
      setPendingChanges([]);

      const doneMsg: Message = {
        id: `msg_${Date.now()}_done`,
        role: 'assistant',
        content: `Final PDF generated with all ${directions.length} changes applied. View it in the **Final Report** tab.`,
        timestamp: Date.now(),
      };

      setNarrativeData((prev) => ({
        ...prev,
        messages: [...prev.messages, doneMsg],
      }));

      return result;
    } catch (error) {
      console.error('Failed to commit changes:', error);

      const errMsg: Message = {
        id: `msg_${Date.now()}_err`,
        role: 'assistant',
        content: 'Failed to commit changes. Please try again.',
        timestamp: Date.now(),
      };

      setNarrativeData((prev) => ({
        ...prev,
        messages: [...prev.messages, errMsg],
      }));

      return null;
    } finally {
      setIsCommitting(false);
    }
  }, [sessionId, pendingChanges]);

  return {
    ...narrativeData,
    sessionState,
    draftPdfUrl,
    finalPdfUrl,
    pendingChanges,
    isCommitting,
    sendMessage,
    removePendingChange,
    commitChanges,
  };
}
