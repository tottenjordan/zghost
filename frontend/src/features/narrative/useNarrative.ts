import { useState, useCallback, useEffect } from 'react';
import { api, gcsToProxyUrl } from '../../services/api';
import type { SessionState } from '../../types/session';
import type { Message, Scene, NarrativeArc, NarrativeData } from './types';

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
  const [refinedReport, setRefinedReport] = useState<string | null>(null);
  const [refinementDirections, setRefinementDirections] = useState<string[]>([]);

  // Auto-load session state on mount
  useEffect(() => {
    if (!sessionId) return;

    const loadSessionData = () => {
      api.getSessionState(sessionId)
        .then((result) => {
          setSessionState(result.state);

          const toHttp = gcsToProxyUrl;

          // Draft PDF: only use if explicitly set in session state
          const draftPdf = result.state?.draft_pdf_url;
          if (draftPdf) {
            setDraftPdfUrl(toHttp(draftPdf));
          }

          // Final PDF: only set after explicit generation
          const finalPdf = result.state?.final_pdf_url;
          if (finalPdf) {
            setFinalPdfUrl(toHttp(finalPdf));
          }
        })
        .catch((err) => console.error('Failed to load session data:', err));
    };

    loadSessionData();
    const intervalId = setInterval(loadSessionData, 3000);
    return () => clearInterval(intervalId);
  }, [sessionId]);

  const sendMessage = useCallback(
    async (content: string) => {
      const userMessage: Message = {
        id: `msg_${Date.now()}`,
        role: 'user',
        content,
        timestamp: Date.now(),
      };

      setNarrativeData((prev) => ({
        ...prev,
        messages: [...prev.messages, userMessage],
        isStreaming: true,
      }));

      if (!sessionId) {
        setNarrativeData((prev) => ({
          ...prev,
          messages: [...prev.messages, {
            id: `msg_${Date.now()}_assistant`,
            role: 'assistant' as const,
            content: 'No session connected.',
            timestamp: Date.now(),
          }],
          isStreaming: false,
        }));
        return;
      }

      try {
        const result = await api.refineNarrative(sessionId, content);
        setRefinedReport(result.refined_text);
        setRefinementDirections((prev) => [...prev, content]);

        setNarrativeData((prev) => ({
          ...prev,
          messages: [...prev.messages, {
            id: `msg_${Date.now()}_assistant`,
            role: 'assistant' as const,
            content: `Done — the report has been updated based on your direction: **"${content}"**.`,
            timestamp: Date.now(),
          }],
          isStreaming: false,
        }));
      } catch (error) {
        console.error('Failed to refine narrative:', error);
        setNarrativeData((prev) => ({
          ...prev,
          messages: [...prev.messages, {
            id: `msg_${Date.now()}_error`,
            role: 'assistant' as const,
            content: 'Failed to refine the narrative. Please try again.',
            timestamp: Date.now(),
          }],
          isStreaming: false,
        }));
      }
    },
    [sessionId]
  );

  const currentReport: string | null =
    refinedReport ??
    (typeof sessionState?.final_report_with_citations === 'string'
      ? sessionState.final_report_with_citations
      : typeof sessionState?.combined_final_cited_report === 'string'
        ? sessionState.combined_final_cited_report
        : null);

  const generatePdf = useCallback(
    async (reportType: 'draft' | 'final' = 'final', content?: string, title?: string) => {
      if (!sessionId) return null;
      try {
        const pdfContent = content ?? (reportType === 'final' ? refinedReport : undefined) ?? undefined;
        const result = await api.generatePdf(sessionId, pdfContent, title, reportType);

        const proxyUrl = gcsToProxyUrl(result.gcs_uri);
        if (reportType === 'draft') {
          setDraftPdfUrl(proxyUrl);
        } else {
          setFinalPdfUrl(proxyUrl);
        }

        return result;
      } catch (error) {
        console.error('Failed to generate PDF:', error);
        return null;
      }
    },
    [sessionId, refinedReport]
  );

  return {
    ...narrativeData,
    sessionState,
    draftPdfUrl,
    finalPdfUrl,
    currentReport,
    refinedReport,
    refinementDirections,
    sendMessage,
    generatePdf,
  };
}
