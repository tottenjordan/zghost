import { useState, useEffect } from 'react';
import { NarrativeChat } from './NarrativeChat';
import { StoryboardView } from './StoryboardView';
import { NarrativeArc } from './NarrativeArc';
import { useNarrative } from './useNarrative';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../components/ui/Tabs';

export function NarrativePage() {
  const [sessionId] = useState<string | null>(() => {
    const params = new URLSearchParams(window.location.search);
    return params.get('session') || null;
  });

  const {
    messages,
    scenes,
    narrativeArc,
    isStreaming,
    sendMessage,
    reorderScenes,
    updateScene,
    updateNarrativeArc,
  } = useNarrative(sessionId);

  // Voice action listener for narrative direction
  useEffect(() => {
    const handler = (e: Event) => {
      const { action, params } = (e as CustomEvent).detail;
      if (action === 'send_narrative_direction' && params?.direction) {
        sendMessage(params.direction);
      }
    };
    window.addEventListener('voice-action', handler);
    return () => window.removeEventListener('voice-action', handler);
  }, [sendMessage]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="mb-2 text-3xl font-bold text-zinc-50">
          Narrative Interface
        </h1>
        <p className="text-zinc-400">
          Collaborate with AI to craft and refine your commercial's story
        </p>
        {sessionId && (
          <p className="mt-1 text-xs text-zinc-600">Session: {sessionId}</p>
        )}
      </div>

      {/* Two-Panel Layout */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Left Panel: Chat */}
        <div className="flex h-[calc(100vh-16rem)] flex-col">
          <NarrativeChat
            messages={messages}
            isStreaming={isStreaming}
            onSendMessage={sendMessage}
          />
        </div>

        {/* Right Panel: Storyboard & Arc */}
        <div className="flex h-[calc(100vh-16rem)] flex-col overflow-y-auto">
          <Tabs defaultValue="storyboard">
            <TabsList className="mb-4">
              <TabsTrigger value="storyboard">
                Storyboard ({scenes.length})
              </TabsTrigger>
              <TabsTrigger value="arc">Narrative Arc</TabsTrigger>
            </TabsList>

            <TabsContent value="storyboard">
              <StoryboardView
                scenes={scenes}
                onReorder={reorderScenes}
                onUpdateScene={updateScene}
              />
            </TabsContent>

            <TabsContent value="arc">
              <NarrativeArc
                narrativeArc={narrativeArc}
                scenes={scenes}
                onUpdate={updateNarrativeArc}
              />
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  );
}
