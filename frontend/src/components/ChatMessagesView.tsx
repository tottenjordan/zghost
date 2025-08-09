import { RefObject, useEffect } from 'react';
import { ScrollArea } from './ui/scroll-area';
import { ActivityTimeline } from './ActivityTimeline';
import { InputForm } from './InputForm';
import { TrendSelector } from './TrendSelector';
import { ArtifactPlaceholder } from './ArtifactPlaceholder';
import { SessionSelector } from './SessionSelector';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { 
  User, Bot, FileText, TrendingUp, Brain, Search, 
  Youtube, Globe, Sparkles, Palette, Image, FileCheck,
  GitMerge, CheckCircle, PenTool, Lightbulb, Video, Loader2,
  ChevronDown, ChevronUp
} from 'lucide-react';

interface MessageWithAgent {
  type: "human" | "ai" | "system";
  content: string;
  id: string;
  agent?: string;
  finalReport?: boolean;
  trendSelection?: boolean;
  pdfData?: string;
  artifacts?: Array<{
    key: string;
    type: 'image' | 'video';
    url?: string;
  }>;
}

interface ProcessedEvent {
  title: string;
  data: any;
}

interface ChatMessagesViewProps {
  messages: MessageWithAgent[];
  isLoading: boolean;
  scrollAreaRef: RefObject<HTMLDivElement>;
  onSubmit: (query: string, pdfFile?: File) => Promise<void>;
  onCancel: () => void;
  displayData: string | null;
  messageEvents: Map<string, ProcessedEvent[]>;
  sourceCount: number;
  googleTrends?: any[];
  youtubeTrends?: any[];
  campaignData?: any;
  onTrendSelect?: (type: 'google' | 'youtube', trend: any) => void;
  sessionId?: string | null;
  userId?: string | null;
  appName?: string | null;
  onSessionChange?: (sessionId: string) => void;
  selectedGoogleTrend?: string | null;
  selectedYoutubeTrend?: string | null;
  trendSelectorVisible?: boolean;
  onToggleTrendSelector?: () => void;
}

const getAgentIcon = (agent?: string) => {
  if (!agent) return Bot;
  
  switch (agent) {
    case 'root_agent':
      return Brain;
    case 'campaign_guide_data_generation_agent':
    case 'campaign_guide_data_extract_agent':
      return FileText;
    case 'trends_and_insights_agent':
      return TrendingUp;
    case 'combined_research_merger':
    case 'combined_research_pipeline':
    case 'merge_planners':
    case 'merge_parallel_insights':
      return GitMerge;
    case 'parallel_planner_agent':
      return Brain;
    case 'yt_sequential_planner':
    case 'yt_analysis_generator':
    case 'yt_web_planner':
    case 'yt_web_searcher':
      return Youtube;
    case 'gs_sequential_planner':
    case 'gs_web_planner':
    case 'gs_web_searcher':
    case 'enhanced_combined_searcher':
      return Search;
    case 'ca_sequential_planner':
    case 'campaign_web_planner':
    case 'campaign_web_searcher':
      return FileText;
    case 'combined_web_evaluator':
      return CheckCircle;
    case 'combined_report_composer':
    case 'combined_report_agent':
      return PenTool;
    case 'ad_content_generator_agent':
      return Sparkles;
    case 'ad_creative_pipeline':
    case 'ad_copy_drafter':
    case 'ad_copy_critic':
    case 'ad_copy_finalizer':
      return Lightbulb;
    case 'visual_generation_pipeline':
    case 'visual_concept_drafter':
    case 'visual_concept_critic':
    case 'visual_concept_finalizer':
      return Palette;
    case 'visual_generator':
      return Image;
    case 'report_generator_agent':
      return FileCheck;
    default:
      return Bot;
  }
};

const formatAgentName = (agent?: string): string => {
  if (!agent) return 'Assistant';
  
  return agent
    .replace(/_agent$/, '')
    .replace(/_/g, ' ')
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
};

const getAgentBackgroundColor = (agent?: string): string => {
  if (!agent) return 'bg-blue-600';
  
  switch (agent) {
    case 'root_agent':
      return 'bg-purple-600';
    case 'campaign_guide_data_generation_agent':
    case 'campaign_guide_data_extract_agent':
      return 'bg-amber-600';
    case 'trends_and_insights_agent':
      return 'bg-indigo-600';
    case 'combined_research_merger':
    case 'merge_planners':
      return 'bg-cyan-600';
    case 'parallel_planner_agent':
    case 'yt_sequential_planner':
      return 'bg-red-600';
    case 'gs_sequential_planner':
    case 'enhanced_combined_searcher':
      return 'bg-green-600';
    case 'ca_sequential_planner':
      return 'bg-orange-600';
    case 'combined_web_evaluator':
      return 'bg-emerald-600';
    case 'combined_report_composer':
      return 'bg-violet-600';
    case 'ad_content_generator_agent':
      return 'bg-pink-600';
    case 'ad_creative_pipeline':
    case 'ad_copy_drafter':
    case 'ad_copy_critic':
      return 'bg-fuchsia-600';
    case 'visual_generation_pipeline':
    case 'visual_concept_drafter':
    case 'visual_concept_critic':
      return 'bg-rose-600';
    case 'visual_generator':
      return 'bg-teal-600';
    case 'report_generator_agent':
      return 'bg-slate-600';
    default:
      return 'bg-blue-600';
  }
};

const getProcessingMessage = (agent?: string, activity?: string): string => {
  if (!agent) return 'Processing your request...';
  
  // Base messages for each agent
  const baseMessages: Record<string, string> = {
    'root_agent': '🤖 Orchestrating agents',
    'campaign_guide_data_generation_agent': '📄 Analyzing campaign guide',
    'campaign_guide_data_extract_agent': '📋 Extracting campaign details',
    'trends_and_insights_agent': '📊 Processing trends and insights',
    'combined_research_merger': '🔍 Coordinating research',
    'combined_research_pipeline': '🔄 Running research pipeline',
    'parallel_planner_agent': '📋 Planning research strategies',
    'yt_sequential_planner': '📺 Analyzing YouTube trends',
    'yt_analysis_generator': '📹 Generating YouTube analysis',
    'yt_web_planner': '📺 Planning YouTube research',
    'yt_web_searcher': '🔎 Searching YouTube insights',
    'gs_sequential_planner': '🔎 Analyzing Google trends',
    'gs_web_planner': '🌐 Planning Google research',
    'gs_web_searcher': '🔍 Searching Google insights',
    'ca_sequential_planner': '📑 Researching campaign',
    'campaign_web_planner': '📋 Planning campaign research',
    'campaign_web_searcher': '🔎 Searching campaign insights',
    'merge_planners': '🔄 Merging research plans',
    'merge_parallel_insights': '🔀 Combining parallel insights',
    'combined_web_evaluator': '✅ Evaluating research quality',
    'enhanced_combined_searcher': '🌐 Enhancing search results',
    'combined_report_composer': '📝 Composing research report',
    'combined_report_agent': '📊 Finalizing research findings',
    'ad_content_generator_agent': '✨ Creating ad campaigns',
    'ad_creative_pipeline': '💡 Crafting ad copy',
    'ad_copy_drafter': '✍️ Drafting ad variations',
    'ad_copy_critic': '🔍 Reviewing ad copy',
    'ad_copy_finalizer': '✅ Finalizing ad copy',
    'visual_generation_pipeline': '🎨 Designing visuals',
    'visual_concept_drafter': '🎨 Creating visual concepts',
    'visual_concept_critic': '👁️ Reviewing concepts',
    'visual_concept_finalizer': '✨ Finalizing visuals',
    'visual_generator': '🖼️ Generating media',
    'report_generator_agent': '📊 Compiling final report'
  };
  
  const baseMessage = baseMessages[agent] || `⚙️ ${agent.replace(/_/g, ' ')}`;
  
  // Add activity context if available
  if (activity) {
    return `${baseMessage} - ${activity}`;
  }
  
  return `${baseMessage}...`;
};

export function ChatMessagesView({
  messages,
  isLoading,
  scrollAreaRef,
  onSubmit,
  onCancel,
  displayData,
  messageEvents,
  sourceCount,
  googleTrends = [],
  youtubeTrends = [],
  campaignData,
  onTrendSelect,
  sessionId,
  userId,
  appName,
  onSessionChange,
  selectedGoogleTrend,
  selectedYoutubeTrend,
  trendSelectorVisible = true,
  onToggleTrendSelector
}: ChatMessagesViewProps) {
  // Show trends when available and there's at least one AI message
  const hasTrends = googleTrends.length > 0 || youtubeTrends.length > 0;
  const shouldShowTrends = hasTrends && messages.some(msg => msg.type === 'ai') && trendSelectorVisible;
  const showToggleButton = hasTrends && (selectedGoogleTrend || selectedYoutubeTrend);
  
  // Debug logging
  console.log('[TrendSelector Debug]', {
    googleTrendsCount: googleTrends.length,
    youtubeTrendsCount: youtubeTrends.length,
    shouldShowTrends,
    trendSelectorVisible,
    selectedGoogleTrend,
    selectedYoutubeTrend,
    showToggleButton
  });
  
  // Scroll to trend selector when it becomes visible
  useEffect(() => {
    if (shouldShowTrends && trendSelectorVisible) {
      setTimeout(() => {
        const trendElement = document.getElementById('trend-selector-container');
        if (trendElement) {
          trendElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }, 100);
    }
  }, [shouldShowTrends, trendSelectorVisible]);

  return (
    <div className="flex-1 flex flex-col h-full relative bg-neutral-800">
      <div className="border-b border-neutral-700 bg-neutral-900 sticky top-0 z-10 shadow-lg shadow-black/20">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white">Marketing Intelligence Chat</h2>
          <div className="flex items-center gap-4">
            {sourceCount > 0 && (
              <span className="text-sm text-neutral-400">
                Sources analyzed: {sourceCount}
              </span>
            )}
            {onSessionChange && (
              <SessionSelector
                currentSessionId={sessionId}
                userId={userId}
                appName={appName}
                onSessionChange={onSessionChange}
              />
            )}
          </div>
        </div>
      </div>

      <ScrollArea className="flex-1 overflow-y-auto" ref={scrollAreaRef}>
        <div className="max-w-6xl mx-auto p-4 space-y-6">
          {messages.map((message) => (
            <div key={message.id} className="space-y-4">
              <div className={`flex gap-3 ${message.type === 'human' ? 'justify-end' : ''}`}>
                {message.type === 'ai' && (
                  <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                    (() => {
                      // Determine the current agent for icon display
                      let currentAgent = message.agent;
                      
                      // If loading and no content, check events for current processing agent
                      if (isLoading && !message.content && message.id.includes('_ai')) {
                        const events = messageEvents.get(message.id);
                        if (events && events.length > 0) {
                          // Search from the end to find the most recent agent activity
                          for (let i = events.length - 1; i >= 0; i--) {
                            const event = events[i];
                            if (event.data && event.data.type === 'functionCall' && event.data.name) {
                              // Extract agent name from function call patterns
                              if (event.data.name.includes('_agent')) {
                                currentAgent = event.data.name;
                                break;
                              }
                            }
                          }
                        }
                      }
                      
                      return currentAgent ? getAgentBackgroundColor(currentAgent) : 'bg-blue-600';
                    })()
                  }`}>
                    {(() => {
                      // Check if this is the latest AI message and we're still loading
                      const isProcessing = isLoading && message.id.includes('_ai') && (!message.content || message.content.includes('Processing'));
                      
                      if (isProcessing) {
                        return <Loader2 className="h-5 w-5 text-white animate-spin" />;
                      }
                      
                      // Determine the current agent for icon
                      let currentAgent = message.agent;
                      
                      // If no agent set, check events for agent info
                      if (!currentAgent && message.id.includes('_ai')) {
                        const events = messageEvents.get(message.id);
                        if (events && events.length > 0) {
                          // Search from the end to find the most recent agent activity
                          for (let i = events.length - 1; i >= 0; i--) {
                            const event = events[i];
                            if (event.data && event.data.type === 'functionCall' && event.data.name) {
                              // Extract agent name from function call patterns
                              if (event.data.name.includes('_agent')) {
                                currentAgent = event.data.name;
                                break;
                              }
                            }
                          }
                        }
                      }
                      
                      const Icon = getAgentIcon(currentAgent);
                      return <Icon className="h-5 w-5 text-white" />;
                    })()}
                  </div>
                )}
                
                <div className={`flex-1 ${message.type === 'human' ? 'max-w-2xl' : ''}`}>
                  <div className={`rounded-2xl p-4 ${
                    message.type === 'human' 
                      ? 'bg-blue-600 text-white ml-auto shadow-lg shadow-blue-600/20' 
                      : 'bg-neutral-900 border border-neutral-700 shadow-lg shadow-black/20'
                  }`}>
                    {message.pdfData && (
                      <div className="flex items-center gap-2 mb-2 text-sm opacity-80">
                        <FileText className="h-4 w-4" />
                        <span>PDF uploaded</span>
                      </div>
                    )}
                    
                    {message.finalReport ? (
                      <div className="space-y-2">
                        <div className="flex items-center gap-2 text-green-400 mb-3">
                          <FileText className="h-5 w-5" />
                          <span className="font-semibold">Final Report Generated</span>
                        </div>
                        <div className="text-neutral-300">
                          {message.content}
                        </div>
                      </div>
                    ) : (
                      <ReactMarkdown 
                        remarkPlugins={[remarkGfm]}
                        className={`prose ${message.type === 'human' ? 'prose-invert' : 'prose-invert'} max-w-none`}
                        components={{
                          p: ({children}) => <p className="mb-2 last:mb-0">{children}</p>,
                          ul: ({children}) => <ul className="list-disc pl-4 mb-2">{children}</ul>,
                          ol: ({children}) => <ol className="list-decimal pl-4 mb-2">{children}</ol>,
                          li: ({children}) => <li className="mb-1">{children}</li>,
                          a: ({href, children}) => (
                            <a 
                              href={href} 
                              target="_blank" 
                              rel="noopener noreferrer"
                              className="text-blue-400 hover:text-blue-300 underline"
                            >
                              {children}
                            </a>
                          ),
                          code: ({className, children, ...props}) => {
                            const match = /language-(\w+)/.exec(className || '');
                            return match ? (
                              <pre className="bg-neutral-900 rounded-lg p-3 overflow-x-auto">
                                <code className={className} {...props}>
                                  {children}
                                </code>
                              </pre>
                            ) : (
                              <code className="bg-neutral-700 px-1 py-0.5 rounded text-sm" {...props}>
                                {children}
                              </code>
                            );
                          }
                        }}
                      >
                        {(() => {
                          // Check if this is a processing message
                          if (isLoading && message.id.includes('_ai') && (!message.content || message.content.includes('Processing'))) {
                            // Check events for the current processing agent
                            const events = messageEvents.get(message.id);
                            let currentProcessingAgent = message.agent;
                            
                            // Look for the latest agent from events
                            if (events && events.length > 0) {
                              // Search from the end to find the most recent agent activity
                              for (let i = events.length - 1; i >= 0; i--) {
                                const event = events[i];
                                if (event.data) {
                                  // Check for agent activity events
                                  if (event.data.type === 'agentActivity' && event.data.agent) {
                                    currentProcessingAgent = event.data.agent;
                                    const activity = event.data.activity;
                                    return getProcessingMessage(currentProcessingAgent, activity);
                                  }
                                  // Also check function calls
                                  else if (event.data.type === 'functionCall' && event.data.name) {
                                    // Try to infer activity from function name
                                    const activity = event.data.name.replace(/_/g, ' ');
                                    return getProcessingMessage(currentProcessingAgent, activity);
                                  }
                                }
                              }
                              
                              const latestEvent = events[events.length - 1];
                              // If we have event data, show more specific info
                              if (latestEvent.data) {
                                if (latestEvent.data.sources_found) {
                                  return `${getProcessingMessage(currentProcessingAgent)} Found ${latestEvent.data.sources_found} sources...`;
                                } else if (latestEvent.data.status) {
                                  return `${getProcessingMessage(currentProcessingAgent)} ${latestEvent.data.status}`;
                                }
                              }
                              
                              return `Processing: ${latestEvent.title}...`;
                            }
                            
                            return getProcessingMessage(currentProcessingAgent);
                          }
                          
                          // Otherwise show the actual content
                          return message.content;
                        })()}
                      </ReactMarkdown>
                    )}
                    
                    {message.agent && (
                      <div className="mt-2 text-xs text-neutral-500">
                        via {formatAgentName(message.agent)}
                      </div>
                    )}
                    
                    {/* Render artifacts */}
                    {message.artifacts && message.artifacts.length > 0 && (
                      <div className="mt-4 space-y-3">
                        {message.artifacts.map((artifact, index) => (
                          <div key={`${artifact.key}-${index}`}>
                            <ArtifactPlaceholder
                              artifactKey={artifact.key}
                              type={artifact.type}
                              sessionId={sessionId}
                              userId={userId}
                            />
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
                
                {message.type === 'human' && (
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-neutral-600 flex items-center justify-center">
                    <User className="h-5 w-5 text-white" />
                  </div>
                )}
              </div>
              
              {messageEvents.get(message.id) && messageEvents.get(message.id)!.length > 0 && (
                <div className="ml-11 mr-4">
                  <ActivityTimeline events={messageEvents.get(message.id)!} />
                </div>
              )}
            </div>
          ))}
          
          {/* Toggle button for trends */}
          {showToggleButton && onToggleTrendSelector && (
            <div className="mt-4 flex justify-center">
              <button
                onClick={onToggleTrendSelector}
                className="flex items-center gap-2 px-4 py-2 bg-neutral-700 hover:bg-neutral-600 rounded-lg transition-colors text-sm"
              >
                <TrendingUp className="h-4 w-4" />
                {trendSelectorVisible ? (
                  <>
                    Hide Trend Selection
                    <ChevronUp className="h-4 w-4" />
                  </>
                ) : (
                  <>
                    Show Trend Selection
                    <ChevronDown className="h-4 w-4" />
                  </>
                )}
              </button>
            </div>
          )}
          
          {shouldShowTrends && onTrendSelect && (
            <div className="mt-6" id="trend-selector-container">
              <TrendSelector
                googleTrends={googleTrends}
                youtubeTrends={youtubeTrends}
                onSelect={onTrendSelect}
                isLoading={isLoading}
                selectedGoogleTrend={selectedGoogleTrend}
                selectedYoutubeTrend={selectedYoutubeTrend}
              />
            </div>
          )}
        </div>
      </ScrollArea>

      <div className="border-t border-neutral-700 bg-neutral-900 p-4 shadow-2xl shadow-black/40">
        <div className="max-w-6xl mx-auto">
          <InputForm 
            onSubmit={onSubmit} 
            isLoading={isLoading}
            embedded={true}
          />
        </div>
      </div>
    </div>
  );
}