import { useState, useCallback, useEffect } from 'react';
import { api } from '../../services/api';
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
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);

  // Auto-load research report and session state on mount
  useEffect(() => {
    if (!sessionId) return;

    const loadSessionData = () => {
      api.getSessionState(sessionId)
        .then((result) => {
          setSessionState(result.state);

          // Check for PDF URLs
          const draftPdf = result.state?.draft_pdf_url;
          const finalPdf = result.state?.final_pdf_url;
          if (finalPdf) {
            setPdfUrl(finalPdf);
          } else if (draftPdf) {
            setPdfUrl(draftPdf);
          }

          const report = result.state?.combined_final_cited_report;
          if (report) {
            setNarrativeData((prev) => ({
              ...prev,
              messages: [
                {
                  id: 'report-initial',
                  role: 'assistant',
                  content:
                    typeof report === 'string'
                      ? report
                      : 'Research report loaded. How would you like to refine it?',
                  timestamp: Date.now(),
                },
              ],
            }));
          }
        })
        .catch((err) => console.error('Failed to load session data:', err));
    };

    // Initial load
    loadSessionData();

    // Poll for updates every 3 seconds
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
        // No backend session — show a local placeholder response
        const assistantMessage: Message = {
          id: `msg_${Date.now()}_assistant`,
          role: 'assistant',
          content: `Received: "${content}". Connect a backend session to get live agent responses.`,
          timestamp: Date.now(),
        };

        setNarrativeData((prev) => ({
          ...prev,
          messages: [...prev.messages, assistantMessage],
          isStreaming: false,
        }));
        return;
      }

      try {
        // Set a 2-minute timeout — the full pipeline takes much longer,
        // so if it hasn't responded quickly this is likely a queued request
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 120_000);

        const responseText = await api.sendMessage(sessionId, content, 'default-user');
        clearTimeout(timeout);

        const assistantMessage: Message = {
          id: `msg_${Date.now()}_assistant`,
          role: 'assistant',
          content: responseText || 'No response received. The agent may still be processing — check the Orchestration tab for pipeline status.',
          timestamp: Date.now(),
        };

        setNarrativeData((prev) => ({
          ...prev,
          messages: [...prev.messages, assistantMessage],
          isStreaming: false,
        }));
      } catch (error) {
        console.error('Failed to send message:', error);
        const errorMsg = error instanceof DOMException && error.name === 'AbortError'
          ? 'Request timed out. The pipeline may still be running — check the Orchestration tab.'
          : 'Failed to get a response. The agent may be busy with the current pipeline run.';
        const assistantMessage: Message = {
          id: `msg_${Date.now()}_error`,
          role: 'assistant',
          content: errorMsg,
          timestamp: Date.now(),
        };
        setNarrativeData((prev) => ({
          ...prev,
          messages: [...prev.messages, assistantMessage],
          isStreaming: false,
        }));
      }
    },
    [sessionId]
  );

  const reorderScenes = useCallback((startIndex: number, endIndex: number) => {
    setNarrativeData((prev) => {
      const newScenes = Array.from(prev.scenes);
      const [removed] = newScenes.splice(startIndex, 1);
      newScenes.splice(endIndex, 0, removed);
      return {
        ...prev,
        scenes: newScenes.map((scene, index) => ({
          ...scene,
          order: index,
          sceneNumber: index + 1,
        })),
      };
    });
  }, []);

  const updateScene = useCallback(
    (sceneId: string, updates: Partial<Scene>) => {
      setNarrativeData((prev) => ({
        ...prev,
        scenes: prev.scenes.map((scene) =>
          scene.id === sceneId ? { ...scene, ...updates } : scene
        ),
      }));
    },
    []
  );

  const updateNarrativeArc = useCallback(
    (arc: Partial<NarrativeArc>) => {
      setNarrativeData((prev) => ({
        ...prev,
        narrativeArc: { ...prev.narrativeArc, ...arc } as NarrativeArc,
      }));
    },
    []
  );

  return {
    ...narrativeData,
    sessionState,
    pdfUrl,
    sendMessage,
    reorderScenes,
    updateScene,
    updateNarrativeArc,
  };
}
