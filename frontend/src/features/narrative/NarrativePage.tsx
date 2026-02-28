import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { NarrativeChat } from './NarrativeChat';
import { StoryboardView } from './StoryboardView';
import { NarrativeArc } from './NarrativeArc';
import { useNarrative } from './useNarrative';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../components/ui/Tabs';
import { Button } from '../../components/ui/Button';
import { CheckCircle, SkipForward } from 'lucide-react';

export function NarrativePage() {
  const navigate = useNavigate();
  const [sessionId] = useState<string | null>(() => {
    const params = new URLSearchParams(window.location.search);
    return params.get('session') || null;
  });

  const {
    messages,
    scenes,
    narrativeArc,
    isStreaming,
    sessionState,
    pdfUrl,
    sendMessage,
    reorderScenes,
    updateScene,
    updateNarrativeArc,
  } = useNarrative(sessionId);

  const hasReport = messages.length > 0 && messages[0].id === 'report-initial';
  const hasPdf = !!pdfUrl;

  const handleAcceptReport = () => {
    sendMessage('I accept this research report. Let\'s proceed to creative development.');
    setTimeout(() => navigate('/orchestration'), 1000);
  };

  const handleSkipToCreative = () => {
    navigate('/orchestration');
  };

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

      {/* Action Bar - shown when report is loaded */}
      {hasReport && (
        <div className="flex items-center gap-3 p-4 bg-blue-950/30 border border-blue-800 rounded-lg">
          <div className="flex-1">
            <h3 className="text-sm font-medium text-blue-300">Research Report Loaded</h3>
            <p className="text-xs text-blue-400/70 mt-0.5">
              Review the report below and decide whether to refine it or proceed to creative development
            </p>
          </div>
          <div className="flex gap-2">
            <Button
              onClick={handleAcceptReport}
              variant="primary"
              size="sm"
              className="flex items-center gap-1.5"
            >
              <CheckCircle className="w-4 h-4" />
              Accept Report
            </Button>
            <Button
              onClick={handleSkipToCreative}
              variant="secondary"
              size="sm"
              className="flex items-center gap-1.5"
            >
              <SkipForward className="w-4 h-4" />
              Skip to Creative
            </Button>
          </div>
        </div>
      )}

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

        {/* Right Panel: PDF Viewer or Storyboard & Arc */}
        <div className="flex h-[calc(100vh-16rem)] flex-col overflow-hidden">
          {hasPdf ? (
            <div className="flex flex-col h-full border border-zinc-800 rounded-lg overflow-hidden bg-zinc-900/50">
              <div className="flex items-center justify-between px-4 py-2 border-b border-zinc-800 bg-zinc-900">
                <h3 className="text-sm font-medium text-zinc-300">
                  {sessionState?.final_pdf_url ? 'Final Report' : 'Draft Report'}
                </h3>
                <span className="text-xs text-zinc-500">
                  {sessionState?.final_pdf_url ? 'Ready for review' : 'Preview'}
                </span>
              </div>
              <div className="flex-1 overflow-hidden">
                <iframe
                  src={pdfUrl}
                  className="w-full h-full"
                  title="Research Report PDF"
                  style={{ border: 'none' }}
                />
              </div>
            </div>
          ) : (
            <div className="overflow-y-auto">
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
          )}
        </div>
      </div>
    </div>
  );
}
