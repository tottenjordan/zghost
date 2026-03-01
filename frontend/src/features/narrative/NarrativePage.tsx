import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { NarrativeChat } from './NarrativeChat';
import { StoryboardView } from './StoryboardView';
import { NarrativeArc } from './NarrativeArc';
import { useNarrative } from './useNarrative';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../components/ui/Tabs';
import { Button } from '../../components/ui/Button';
import { Markdown } from '../../components/ui/Markdown';
import { CheckCircle, SkipForward, ChevronDown, AlertCircle, FileText, Loader2 } from 'lucide-react';
import { useCampaignStore } from '../../stores/campaignStore';
import { cn } from '../../lib/utils';

export function NarrativePage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { sessions } = useCampaignStore();

  const [sessionId, setSessionId] = useState<string | null>(() => {
    return searchParams.get('session') || null;
  });

  const [pdfError, setPdfError] = useState(false);

  const handleSelectSession = (newSessionId: string) => {
    setSessionId(newSessionId);
    setSearchParams({ session: newSessionId });
  };

  const [isGeneratingPdf, setIsGeneratingPdf] = useState(false);

  const {
    messages,
    scenes,
    narrativeArc,
    isStreaming,
    sessionState,
    pdfUrl,
    sendMessage,
    generatePdf,
    reorderScenes,
    updateScene,
    updateNarrativeArc,
  } = useNarrative(sessionId);

  const hasReport = messages.length > 0 && messages[0].id === 'report-initial';
  const hasPdf = !!pdfUrl;

  // Reset PDF error when URL changes
  useEffect(() => {
    setPdfError(false);
  }, [pdfUrl]);

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
    <div className="flex flex-col h-full gap-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="mb-2 text-3xl font-bold text-zinc-50">
            Narrative Interface
          </h1>
          <p className="text-zinc-400">
            Collaborate with AI to craft and refine your commercial's story
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
              onClick={async () => {
                if (!sessionId) return;
                setIsGeneratingPdf(true);
                try {
                  await generatePdf();
                  // Open the PDF in a new tab via backend proxy
                  window.open(`/api/v1/narrative/pdf/${sessionId}/download`, '_blank');
                } finally {
                  setIsGeneratingPdf(false);
                }
              }}
              variant="secondary"
              size="sm"
              className="flex items-center gap-1.5"
              disabled={isGeneratingPdf}
            >
              {isGeneratingPdf ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <FileText className="w-4 h-4" />
              )}
              {isGeneratingPdf ? 'Generating...' : 'Generate PDF'}
            </Button>
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
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2 flex-1 min-h-0">
        {/* Left Panel: Chat */}
        <div className="flex flex-col min-h-[300px] lg:h-auto">
          <NarrativeChat
            messages={messages}
            isStreaming={isStreaming}
            onSendMessage={sendMessage}
            sources={sessionState?.sources}
          />
        </div>

        {/* Right Panel: PDF Viewer or Storyboard & Arc */}
        <div className="flex flex-col min-h-[300px] lg:h-auto overflow-hidden">
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
                {pdfError ? (
                  <div className="h-full overflow-y-auto p-4">
                    <div className="flex items-center gap-2 p-3 mb-4 bg-amber-950/30 border border-amber-800/50 rounded-lg">
                      <AlertCircle className="w-4 h-4 text-amber-400 flex-shrink-0" />
                      <p className="text-sm text-amber-300">
                        PDF failed to load. Showing markdown report instead.
                      </p>
                    </div>
                    <div className="prose prose-invert max-w-none">
                      <Markdown
                        content={
                          sessionState?.final_report_with_citations ||
                          sessionState?.combined_final_cited_report ||
                          'Report content not available.'
                        }
                        sources={sessionState?.sources}
                      />
                    </div>
                  </div>
                ) : (
                  <iframe
                    src={pdfUrl}
                    className="w-full h-full"
                    title="Research Report PDF"
                    style={{ border: 'none' }}
                    onError={() => setPdfError(true)}
                  />
                )}
              </div>
            </div>
          ) : (
            <div className="overflow-y-auto overflow-x-auto">
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
