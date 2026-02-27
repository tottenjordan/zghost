import { useState, useCallback } from 'react';
import { api } from '../../services/api';
import type { Message, Scene, NarrativeArc, NarrativeData } from './types';

export function useNarrative(sessionId: string | null) {
  const [narrativeData, setNarrativeData] = useState<NarrativeData>({
    messages: [],
    scenes: [],
    narrativeArc: undefined,
    isStreaming: false,
  });

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
        const responseText = await api.sendMessage(sessionId, content, 'default-user');

        const assistantMessage: Message = {
          id: `msg_${Date.now()}_assistant`,
          role: 'assistant',
          content: responseText || 'No response',
          timestamp: Date.now(),
        };

        setNarrativeData((prev) => ({
          ...prev,
          messages: [...prev.messages, assistantMessage],
          isStreaming: false,
        }));
      } catch (error) {
        console.error('Failed to send message:', error);
        setNarrativeData((prev) => ({
          ...prev,
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
    sendMessage,
    reorderScenes,
    updateScene,
    updateNarrativeArc,
  };
}
