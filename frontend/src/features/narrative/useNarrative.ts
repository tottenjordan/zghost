import { useState, useCallback, useEffect } from 'react';
import { api, gcsToProxyUrl } from '../../services/api';
import type { SessionState } from '../../types/session';
import type { Message, Scene, NarrativeArc, NarrativeData } from './types';

const GCS_BUCKET = import.meta.env.VITE_GCS_BUCKET || 'zghost-media-center';

export function useNarrative(sessionId: string | null) {
  const [narrativeData, setNarrativeData] = useState<NarrativeData>({
    messages: [],
    scenes: [],
    narrativeArc: undefined,
    isStreaming: false,
  });
  const [sessionState, setSessionState] = useState<SessionState>({});
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);

  // Load saved messages from localStorage on mount
  useEffect(() => {
    if (!sessionId) return;

    const storageKey = `narrative-chat-${sessionId}`;
    const savedMessages = localStorage.getItem(storageKey);

    if (savedMessages) {
      try {
        const parsedMessages = JSON.parse(savedMessages);
        setNarrativeData((prev) => ({
          ...prev,
          messages: parsedMessages,
        }));
      } catch (err) {
        console.error('Failed to parse saved messages:', err);
      }
    }
  }, [sessionId]);

  // Save messages to localStorage whenever they change
  useEffect(() => {
    if (!sessionId || narrativeData.messages.length === 0) return;

    const storageKey = `narrative-chat-${sessionId}`;
    localStorage.setItem(storageKey, JSON.stringify(narrativeData.messages));
  }, [sessionId, narrativeData.messages]);

  // Auto-load research report and session state on mount
  useEffect(() => {
    if (!sessionId) return;

    const loadSessionData = () => {
      api.getSessionState(sessionId)
        .then((result) => {
          setSessionState(result.state);

          // Check for PDF URLs — proxy through backend
          const toHttp = gcsToProxyUrl;
          const draftPdf = result.state?.draft_pdf_url;
          const finalPdf = result.state?.final_pdf_url;
          if (finalPdf) {
            setPdfUrl(toHttp(finalPdf));
          } else if (draftPdf) {
            setPdfUrl(toHttp(draftPdf));
          }

          // Auto-populate storyboard scenes from pipeline artifacts
          const imgKeys = result.state?.img_artifact_keys?.img_artifact_keys || result.state?.img_artifact_keys || [];
          const vidKeys = result.state?.vid_artifact_keys?.vid_artifact_keys || result.state?.vid_artifact_keys || [];
          const gcsFolder = result.state?.gcs_folder || '';
          const commercialDuration = result.state?.commercial_duration || 30;

          const mediaItems: Array<{
            url: string;
            headline?: string;
            concept?: string;
            caption?: string;
            prompt?: string;
            type: 'image' | 'video';
          }> = [];

          // Parse image artifacts
          (Array.isArray(imgKeys) ? imgKeys : []).forEach((item: any) => {
            if (typeof item === 'string') {
              const url = item.startsWith('gs://') ? item : `gs://${GCS_BUCKET}/${gcsFolder}/${item}`;
              mediaItems.push({ url, type: 'image' });
            } else if (item && typeof item === 'object') {
              const artifactKey = item.artifact_key || item.name || item.filename || '';
              const url = artifactKey.startsWith('gs://')
                ? artifactKey
                : `gs://${GCS_BUCKET}/${gcsFolder}/${artifactKey}`;
              mediaItems.push({
                url,
                type: 'image',
                headline: item.headline,
                concept: item.concept,
                caption: item.caption,
                prompt: item.img_prompt || item.prompt,
              });
            }
          });

          // Parse video artifacts
          (Array.isArray(vidKeys) ? vidKeys : []).forEach((item: any) => {
            if (typeof item === 'string') {
              const url = item.startsWith('gs://') ? item : `gs://${GCS_BUCKET}/${gcsFolder}/${item}`;
              mediaItems.push({ url, type: 'video' });
            } else if (item && typeof item === 'object') {
              const artifactKey = item.artifact_key || item.name || item.filename || '';
              const url = artifactKey.startsWith('gs://')
                ? artifactKey
                : `gs://${GCS_BUCKET}/${gcsFolder}/${artifactKey}`;
              mediaItems.push({
                url,
                type: 'video',
                headline: item.headline,
                concept: item.concept,
                caption: item.caption,
                prompt: item.vid_prompt || item.prompt,
              });
            }
          });

          // Create scenes from media items
          if (mediaItems.length > 0) {
            const narrativeBeats: Scene['narrativeBeat'][] = ['setup', 'rising_action', 'climax', 'resolution'];
            const sceneDuration = commercialDuration / mediaItems.length;

            const newScenes: Scene[] = mediaItems.map((media, index) => {
              const beatIndex = Math.floor((index / mediaItems.length) * narrativeBeats.length);
              const beat = narrativeBeats[Math.min(beatIndex, narrativeBeats.length - 1)];

              return {
                id: `scene-${index}`,
                order: index,
                sceneNumber: index + 1,
                frameUrl: toHttp(media.url),
                description: [media.headline, media.caption, media.concept]
                  .filter(Boolean)
                  .join(' — ') || `Scene ${index + 1}`,
                duration: Math.round(sceneDuration * 10) / 10,
                narrativeBeat: beat,
                prompt: media.prompt,
              };
            });

            setNarrativeData((prev) => ({
              ...prev,
              scenes: newScenes,
            }));
          }

          // Prefer the citation-processed version over the raw report
          const report = result.state?.final_report_with_citations || result.state?.combined_final_cited_report;
          if (report) {
            // If a PDF is available, show a brief message instead of dumping full markdown
            const hasPdfAvailable = result.state?.final_pdf_url || result.state?.draft_pdf_url;
            const chatContent = hasPdfAvailable
              ? 'Research report is ready — view it in the PDF panel on the right. You can chat here to refine the narrative, ask questions about the report, or give creative direction.'
              : typeof report === 'string'
                ? report
                : 'Research report loaded. How would you like to refine it?';

            setNarrativeData((prev) => {
              // Check if report-initial message already exists
              const hasReportMessage = prev.messages.some((msg) => msg.id === 'report-initial');

              // If we already have saved messages with the report, don't add it again
              if (hasReportMessage) {
                return prev;
              }

              // Otherwise, add the report message to any existing messages
              return {
                ...prev,
                messages: [
                  {
                    id: 'report-initial',
                    role: 'assistant',
                    content: chatContent,
                    timestamp: Date.now(),
                  },
                  ...prev.messages,
                ],
              };
            });
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
        // Use the lightweight narrative refinement endpoint (not the full pipeline)
        const result = await api.refineNarrative(sessionId, content);

        const assistantMessage: Message = {
          id: `msg_${Date.now()}_assistant`,
          role: 'assistant',
          content: result.refined_text,
          timestamp: Date.now(),
        };

        setNarrativeData((prev) => ({
          ...prev,
          messages: [...prev.messages, assistantMessage],
          isStreaming: false,
        }));
      } catch (error) {
        console.error('Failed to refine narrative:', error);
        const assistantMessage: Message = {
          id: `msg_${Date.now()}_error`,
          role: 'assistant',
          content: 'Failed to refine the narrative. Please try again.',
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

  const generatePdf = useCallback(
    async (content?: string, title?: string) => {
      if (!sessionId) return null;
      try {
        const result = await api.generatePdf(sessionId, content, title);
        // Don't set pdfUrl here — keep the storyboard view visible.
        // The caller opens the PDF in a new tab via the backend proxy.
        return result;
      } catch (error) {
        console.error('Failed to generate PDF:', error);
        return null;
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
    generatePdf,
    reorderScenes,
    updateScene,
    updateNarrativeArc,
  };
}
