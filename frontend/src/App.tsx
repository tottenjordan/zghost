import { useState, useRef, useCallback, useEffect } from "react";
import { v4 as uuidv4 } from 'uuid';
import { WelcomeScreen } from "@/components/WelcomeScreen";
import { ChatMessagesView } from "@/components/ChatMessagesView";

type DisplayData = string | null;

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
    type: 'image' | 'video' | 'pdf';
    url?: string;
    gcsUrl?: string;
  }>;
}

interface AgentMessage {
  parts: { text: string }[];
  role: string;
}

interface AgentResponse {
  content: AgentMessage;
  usageMetadata: {
    candidatesTokenCount: number;
    promptTokenCount: number;
    totalTokenCount: number;
  };
  author: string;
  actions: {
    stateDelta: {
      research_plan?: string;
      final_report?: boolean;
      google_trends?: any[];
      youtube_trends?: any[];
      campaign_guide_data?: any;
    };
  };
}

interface ProcessedEvent {
  title: string;
  data: any;
}

export default function App() {
  const [userId, setUserId] = useState<string | null>("u_999");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [appName, setAppName] = useState<string | null>("trends_and_insights_agent");
  const [messages, setMessages] = useState<MessageWithAgent[]>([]);
  const [displayData, setDisplayData] = useState<DisplayData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [messageEvents, setMessageEvents] = useState<Map<string, ProcessedEvent[]>>(new Map());
  const [sourceCount, setSourceCount] = useState<number>(0);
  const [isBackendReady, setIsBackendReady] = useState(false);
  const [isCheckingBackend, setIsCheckingBackend] = useState(true);
  const [googleTrends, setGoogleTrends] = useState<any[]>([]);
  const [youtubeTrends, setYoutubeTrends] = useState<any[]>([]);
  const [campaignData, setCampaignData] = useState<any>(null);
  const [selectedGoogleTrend, setSelectedGoogleTrend] = useState<string | null>(null);
  const [selectedYoutubeTrend, setSelectedYoutubeTrend] = useState<string | null>(null);
  const [trendSelectorVisible, setTrendSelectorVisible] = useState(true);
  const currentAgentRef = useRef('');
  const currentActivityRef = useRef('');
  const accumulatedTextRef = useRef("");
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  const retryWithBackoff = async (
    fn: () => Promise<any>,
    maxRetries: number = 10,
    maxDuration: number = 120000
  ): Promise<any> => {
    const startTime = Date.now();
    let lastError: Error;
    
    for (let attempt = 0; attempt < maxRetries; attempt++) {
      if (Date.now() - startTime > maxDuration) {
        throw new Error(`Retry timeout after ${maxDuration}ms`);
      }
      
      try {
        return await fn();
      } catch (error) {
        lastError = error as Error;
        const delay = Math.min(1000 * Math.pow(2, attempt), 5000);
        console.log(`Attempt ${attempt + 1} failed, retrying in ${delay}ms...`, error);
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }
    
    throw lastError!;
  };

  const createSession = async (): Promise<{userId: string, sessionId: string, appName: string}> => {
    const generatedSessionId = uuidv4();
    const response = await fetch(`/api/apps/trends_and_insights_agent/users/u_999/sessions/${generatedSessionId}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({})
    });
    
    if (!response.ok) {
      throw new Error(`Failed to create session: ${response.status} ${response.statusText}`);
    }
    
    const data = await response.json();
    return {
      userId: data.userId,
      sessionId: data.id,
      appName: data.appName
    };
  };

  const checkBackendHealth = async (): Promise<boolean> => {
    try {
      const response = await fetch("/api/list-apps", {
        method: "GET",
        headers: {
          "Content-Type": "application/json"
        }
      });
      return response.ok;
    } catch (error) {
      console.log("Backend not ready yet:", error);
      return false;
    }
  };

  const extractDataFromSSE = (data: string) => {
    try {
      const parsed = JSON.parse(data);
      console.log('[SSE PARSED EVENT]:', JSON.stringify(parsed, null, 2));

      let textParts: string[] = [];
      let agent = '';
      let activity = '';
      let finalReport = undefined;
      let functionCall = null;
      let functionResponse = null;
      let sources = null;
      let trends = null;
      let campaignGuideData = null;
      let artifacts = null;
      let gcsFolder = null;
      let gcsBucket = null;

      if (parsed.content && parsed.content.parts) {
        textParts = parsed.content.parts
          .filter((part: any) => part.text)
          .map((part: any) => part.text);
        
        const functionCallPart = parsed.content.parts.find((part: any) => part.functionCall);
        if (functionCallPart) {
          functionCall = functionCallPart.functionCall;
        }
        
        const functionResponsePart = parsed.content.parts.find((part: any) => part.functionResponse);
        if (functionResponsePart) {
          functionResponse = functionResponsePart.functionResponse;
        }
      }

      if (parsed.author) {
        agent = parsed.author;
        console.log('[SSE EXTRACT] Agent:', agent);
      }
      
      // Extract activity from function calls or state changes
      if (functionCall) {
        switch (functionCall.name) {
          case 'search_web':
          case 'web_search':
            activity = `Searching for ${functionCall.args?.query || 'information'}`;
            break;
          case 'generate_image':
            activity = 'Generating image';
            break;
          case 'generate_video':
            activity = 'Creating video';
            break;
          case 'save_img_artifact_key':
            activity = 'Saving image';
            break;
          case 'save_vid_artifact_key':
            activity = 'Saving video';
            break;
          case 'save_yt_trends_to_session_state':
            activity = 'Saving YouTube trends to session state';
            break;
          case 'save_search_trends_to_session_state':
            activity = 'Saving search trends to session state';
            break;
          case 'ad_creative_pipeline':
            activity = 'Crafting ad copy';
            break;
          case 'visual_generation_pipeline':
            activity = 'Designing visual concepts';
            break;
          default:
            activity = functionCall.name.replace(/_/g, ' ');
        }
      }

      if (
        parsed.actions &&
        parsed.actions.stateDelta
      ) {
        if (parsed.actions.stateDelta.final_report) {
          finalReport = parsed.actions.stateDelta.final_report;
        }
        
        if (parsed.actions.stateDelta.google_trends) {
          trends = { type: 'google', data: parsed.actions.stateDelta.google_trends };
        }
        
        if (parsed.actions.stateDelta.youtube_trends) {
          trends = { type: 'youtube', data: parsed.actions.stateDelta.youtube_trends };
        }
        
        if (parsed.actions.stateDelta.campaign_guide_data) {
          campaignGuideData = parsed.actions.stateDelta.campaign_guide_data;
        }
        
        // Extract GCS information if available
        if (parsed.actions.stateDelta.gcs_folder) {
          gcsFolder = parsed.actions.stateDelta.gcs_folder;
          console.log('[SSE EXTRACT] gcs_folder:', gcsFolder);
        }
        
        if (parsed.actions.stateDelta.gcs_bucket) {
          gcsBucket = parsed.actions.stateDelta.gcs_bucket;
          console.log('[SSE EXTRACT] gcs_bucket:', gcsBucket);
        }
        
        // Extract image and video artifacts
        if (parsed.actions.stateDelta.img_artifact_keys) {
          console.log('[SSE EXTRACT] img_artifact_keys:', parsed.actions.stateDelta.img_artifact_keys);
          const imgArtifacts = parsed.actions.stateDelta.img_artifact_keys.img_artifact_keys || [];
          if (!artifacts) artifacts = [];
          imgArtifacts.forEach((artifact: any) => {
            artifacts.push({
              key: artifact.artifact_key,
              type: 'image' as const,
              url: artifact.artifact_key
            });
          });
        }
        
        if (parsed.actions.stateDelta.vid_artifact_keys) {
          console.log('[SSE EXTRACT] vid_artifact_keys:', parsed.actions.stateDelta.vid_artifact_keys);
          const vidArtifacts = parsed.actions.stateDelta.vid_artifact_keys.vid_artifact_keys || [];
          if (!artifacts) artifacts = [];
          vidArtifacts.forEach((artifact: any) => {
            artifacts.push({
              key: artifact.artifact_key,
              type: 'video' as const,
              url: artifact.artifact_key
            });
          });
        }
        
        // Check for PDF artifacts (reports)
        if (parsed.actions.stateDelta.pdf_artifact_keys) {
          console.log('[SSE EXTRACT] pdf_artifact_keys:', parsed.actions.stateDelta.pdf_artifact_keys);
          const pdfArtifacts = parsed.actions.stateDelta.pdf_artifact_keys.pdf_artifact_keys || [];
          if (!artifacts) artifacts = [];
          pdfArtifacts.forEach((artifact: any) => {
            artifacts.push({
              key: artifact.artifact_key,
              type: 'pdf' as const,
              url: artifact.artifact_key
            });
          });
        }
        
        // Also check for specific report artifacts
        if (parsed.actions.stateDelta.report_artifact_key) {
          console.log('[SSE EXTRACT] report_artifact_key:', parsed.actions.stateDelta.report_artifact_key);
          if (!artifacts) artifacts = [];
          artifacts.push({
            key: parsed.actions.stateDelta.report_artifact_key,
            type: 'pdf' as const,
            url: parsed.actions.stateDelta.report_artifact_key
          });
        }
      }

      let sourceCount = 0;
      if ((parsed.author === 'combined_research_merger' || parsed.author === 'enhanced_combined_searcher')) {
        console.log('[SSE EXTRACT] Relevant agent for source count:', parsed.author);
        if (parsed.actions?.stateDelta?.url_to_short_id) {
          sourceCount = Object.keys(parsed.actions.stateDelta.url_to_short_id).length;
          console.log('[SSE EXTRACT] Calculated sourceCount:', sourceCount);
        }
      }

      if (parsed.actions?.stateDelta?.sources) {
        sources = parsed.actions.stateDelta.sources;
        console.log('[SSE EXTRACT] Sources found:', sources);
      }

      // Store GCS info globally if we find it
      if (gcsFolder || gcsBucket) {
        (window as any).__gcsInfo = { folder: gcsFolder, bucket: gcsBucket };
      }
      
      return { textParts, agent, activity, finalReport, functionCall, functionResponse, sourceCount, sources, trends, campaignGuideData, artifacts, gcsFolder, gcsBucket };
    } catch (error) {
      const truncatedData = data.length > 200 ? data.substring(0, 200) + "..." : data;
      console.error('Error parsing SSE data. Raw data (truncated): "', truncatedData, '". Error details:', error);
      return { textParts: [], agent: '', activity: '', finalReport: undefined, functionCall: null, functionResponse: null, sourceCount: 0, sources: null, trends: null, campaignGuideData: null, artifacts: null, gcsFolder: null, gcsBucket: null };
    }
  };

  const getEventTitle = (agentName: string): string => {
    switch (agentName) {
      case "root_agent":
        return "Orchestrating Agents";
      case "campaign_guide_data_generation_agent":
        return "Processing Campaign Guide";
      case "trends_and_insights_agent":
        return "Analyzing Trends";
      case "combined_research_merger":
        return "Coordinating Research";
      case "combined_research_pipeline":
        return "Research Pipeline";
      case "merge_parallel_insights":
        return "Parallel Research";
      case "parallel_planner_agent":
        return "Planning Research";
      case "yt_sequential_planner":
        return "YouTube Analysis";
      case "gs_sequential_planner":
        return "Google Search Analysis";
      case "ca_sequential_planner":
        return "Campaign Research";
      case "merge_planners":
        return "Merging Research Plans";
      case "combined_web_evaluator":
        return "Quality Check";
      case "enhanced_combined_searcher":
        return "Enhanced Search";
      case "combined_report_composer":
        return "Composing Report";
      case "ad_content_generator_agent":
        return "Generating Ad Content";
      case "ad_creative_pipeline":
        return "Ad Copy Generation";
      case "visual_generation_pipeline":
        return "Visual Concept Development";
      case "visual_generator":
        return "Generating Visuals";
      case "report_generator_agent":
        return "Compiling PDF Report";
      default:
        return `Processing (${agentName || 'Unknown Agent'})`;
    }
  };

  const getProcessingMessage = (agent?: string, activity?: string): string => {
    console.log('[getProcessingMessage] Called with agent:', agent, 'activity:', activity);
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

  const processSseEventData = (jsonData: string, aiMessageId: string) => {
    const { textParts, agent, activity, finalReport, functionCall, functionResponse, sourceCount, sources, trends, campaignGuideData, artifacts, gcsFolder, gcsBucket } = extractDataFromSSE(jsonData);

    if (sourceCount > 0) {
      console.log('[SSE HANDLER] Updating sourceCount. Current sourceCount:', sourceCount);
      setSourceCount(prev => Math.max(prev, sourceCount));
    }

    if (agent && agent !== currentAgentRef.current) {
      currentAgentRef.current = agent;
    }
    
    if (activity) {
      currentActivityRef.current = activity;
    }

    if (trends) {
      console.log('[Trends Update]', trends);
      if (trends.type === 'google') {
        setGoogleTrends(trends.data);
        console.log('[Google Trends Set]', trends.data.length, 'trends');
      } else if (trends.type === 'youtube') {
        setYoutubeTrends(trends.data);
        console.log('[YouTube Trends Set]', trends.data.length, 'trends');
      }
    }

    if (campaignGuideData) {
      setCampaignData(campaignGuideData);
    }

    if (functionCall) {
      const functionCallTitle = `Function Call: ${functionCall.name}`;
      console.log('[SSE HANDLER] Adding Function Call timeline event:', functionCallTitle);
      setMessageEvents(prev => new Map(prev).set(aiMessageId, [...(prev.get(aiMessageId) || []), {
        title: functionCallTitle,
        data: { type: 'functionCall', name: functionCall.name, args: functionCall.args, id: functionCall.id }
      }]));
    }

    if (functionResponse) {
      const functionResponseTitle = `Function Response: ${functionResponse.name}`;
      console.log('[SSE HANDLER] Adding Function Response timeline event:', functionResponseTitle);
      setMessageEvents(prev => new Map(prev).set(aiMessageId, [...(prev.get(aiMessageId) || []), {
        title: functionResponseTitle,
        data: { type: 'functionResponse', name: functionResponse.name, response: functionResponse.response, id: functionResponse.id }
      }]));
    }

    // Update the agent first to show processing status
    if (agent && agent !== currentAgentRef.current) {
      console.log('[AGENT UPDATE] Changing from', currentAgentRef.current, 'to', agent);
      currentAgentRef.current = agent;
      setMessages(prev => {
        const newContent = accumulatedTextRef.current || getProcessingMessage(agent, currentActivityRef.current);
        console.log(`[MESSAGE UPDATE] Agent ${agent} update:`, newContent);
        return prev.map(msg =>
          msg.id === aiMessageId ? { ...msg, agent: agent, content: newContent } : msg
        );
      });
    } else if (activity && !accumulatedTextRef.current) {
      // Update activity even if agent hasn't changed
      console.log('[ACTIVITY UPDATE]', activity, 'for agent', currentAgentRef.current || agent);
      setMessages(prev => {
        const newContent = getProcessingMessage(currentAgentRef.current || agent, activity);
        console.log(`[MESSAGE UPDATE] Activity update:`, newContent);
        return prev.map(msg =>
          msg.id === aiMessageId ? { ...msg, content: newContent } : msg
        );
      });
    }
    
    // Always add agent activity to timeline events for better tracking
    if (agent && (functionCall || activity)) {
      const eventTitle = getEventTitle(agent);
      console.log('[SSE HANDLER] Adding Agent Activity event:', agent, activity || functionCall?.name);
      setMessageEvents(prev => new Map(prev).set(aiMessageId, [...(prev.get(aiMessageId) || []), {
        title: eventTitle,
        data: { 
          type: 'agentActivity', 
          agent: agent, 
          activity: activity || functionCall?.name || 'Processing',
          timestamp: Date.now()
        }
      }]));
    }
    
    if (textParts.length > 0 && agent !== "report_generator_agent") {
      // Always update the message content for any agent
      for (const text of textParts) {
        accumulatedTextRef.current += text + " ";
        setMessages(prev => prev.map(msg =>
          msg.id === aiMessageId ? { ...msg, content: accumulatedTextRef.current.trim(), agent: currentAgentRef.current || msg.agent } : msg
        ));
        setDisplayData(accumulatedTextRef.current.trim());
      }
      
      // Also add to timeline events for non-root agents
      if (agent !== "root_agent") {
        const eventTitle = getEventTitle(agent);
        console.log('[SSE HANDLER] Adding Text timeline event for agent:', agent, 'Title:', eventTitle, 'Data:', textParts.join(" "));
        setMessageEvents(prev => new Map(prev).set(aiMessageId, [...(prev.get(aiMessageId) || []), {
          title: eventTitle,
          data: { type: 'text', content: textParts.join(" ") }
        }]));
      }
    } else if (agent && textParts.length === 0) {
      // Handle agents that send empty responses
      console.log('[EMPTY RESPONSE] Agent', agent, 'sent empty response with activity:', activity);
      // Always update the message to show current agent and activity
      setMessages(prev => prev.map(msg =>
        msg.id === aiMessageId ? { 
          ...msg, 
          content: accumulatedTextRef.current || getProcessingMessage(agent, activity || currentActivityRef.current), 
          agent: agent 
        } : msg
      ));
    }

    if (sources) {
      console.log('[SSE HANDLER] Adding Retrieved Sources timeline event:', sources);
      setMessageEvents(prev => new Map(prev).set(aiMessageId, [...(prev.get(aiMessageId) || []), {
        title: "Retrieved Sources", data: { type: 'sources', content: sources }
      }]));
    }

    if (agent === "report_generator_agent" && finalReport) {
      const finalReportMessageId = Date.now().toString() + "_final";
      setMessages(prev => [...prev, { type: "ai", content: finalReport as string, id: finalReportMessageId, agent: currentAgentRef.current, finalReport: true }]);
      setDisplayData(finalReport as string);
    }
    
    // Handle artifacts from visual_generator
    if (artifacts && artifacts.length > 0 && sessionId && userId && appName) {
      // Update artifact URLs with proper session context
      const artifactsWithUrls = artifacts.map(artifact => ({
        ...artifact,
        url: `/api/apps/${appName}/users/${userId}/sessions/${sessionId}/artifacts/${artifact.key}`
      }));
      
      console.log('[SSE HANDLER] Adding artifacts to message:', artifactsWithUrls);
      setMessages(prev => prev.map(msg =>
        msg.id === aiMessageId ? { ...msg, artifacts: [...(msg.artifacts || []), ...artifactsWithUrls] } : msg
      ));
      
      // Add artifacts to timeline events
      artifactsWithUrls.forEach(artifact => {
        const artifactTitle = artifact.type === 'image' ? 'Generated Image' : 
                              artifact.type === 'video' ? 'Generated Video' : 'PDF Report';
        setMessageEvents(prev => new Map(prev).set(aiMessageId, [...(prev.get(aiMessageId) || []), {
          title: artifactTitle,
          data: { type: 'artifact', artifact }
        }]));
      });
    }
  };

  const handleSubmit = useCallback(async (query: string, pdfFile?: File) => {
    if (!query.trim() && !pdfFile) return;

    setIsLoading(true);
    try {
      let currentUserId = userId;
      let currentSessionId = sessionId;
      let currentAppName = appName;
      
      if (!currentSessionId || !currentUserId || !currentAppName) {
        console.log('Creating new session...');
        const sessionData = await retryWithBackoff(createSession);
        currentUserId = sessionData.userId;
        currentSessionId = sessionData.sessionId;
        currentAppName = sessionData.appName;
        
        setUserId(currentUserId);
        setSessionId(currentSessionId);
        setAppName(currentAppName);
        console.log('Session created successfully:', { currentUserId, currentSessionId, currentAppName });
      }

      let finalQuery = query;
      let pdfData: string | undefined;
      
      if (pdfFile) {
        const reader = new FileReader();
        pdfData = await new Promise<string>((resolve, reject) => {
          reader.onload = (e) => resolve(e.target?.result as string);
          reader.onerror = reject;
          reader.readAsDataURL(pdfFile);
        });
        finalQuery = `use this pdf ${pdfFile.name}`;
        
        const userMessageId = Date.now().toString();
        setMessages(prev => [...prev, { 
          type: "human", 
          content: finalQuery, 
          id: userMessageId,
          pdfData: pdfData
        }]);
      } else {
        const userMessageId = Date.now().toString();
        setMessages(prev => [...prev, { type: "human", content: query, id: userMessageId }]);
      }

      const aiMessageId = Date.now().toString() + "_ai";
      currentAgentRef.current = '';
      accumulatedTextRef.current = '';

      const initialMessage = {
        type: "ai" as const,
        content: "🔄 Processing your request...",
        id: aiMessageId,
        agent: '',
      };
      console.log('[MESSAGE UPDATE] Initial message:', initialMessage);
      setMessages(prev => [...prev, initialMessage]);

      const sendMessage = async () => {
        const response = await fetch("/api/run", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            appName: currentAppName,
            userId: currentUserId,
            sessionId: currentSessionId,
            newMessage: {
              parts: pdfData ? [
                { text: finalQuery },
                { inlineData: { data: pdfData.split(',')[1], mimeType: 'application/pdf' } }
              ] : [{ text: finalQuery }],
              role: "user"
            },
            streaming: false
          }),
        });

        if (!response.ok) {
          throw new Error(`Failed to send message: ${response.status} ${response.statusText}`);
        }
        
        return response;
      };

      const response = await retryWithBackoff(sendMessage);

      // Handle non-streaming JSON array response
      const events = await response.json();
      console.log('[API RESPONSE] Received events:', events.length);
      
      // Process each event in the array
      for (let i = 0; i < events.length; i++) {
        const event = events[i];
        console.log(`[PROCESSING EVENT ${i+1}/${events.length}]:`, event);
        
        // Log specific event details for debugging
        if (event.author) {
          console.log(`  Agent: ${event.author}`);
        }
        if (event.content?.parts) {
          const hasText = event.content.parts.some((p: any) => p.text);
          const functionCalls = event.content.parts.filter((p: any) => p.functionCall);
          console.log(`  Content: ${hasText ? 'Has text' : 'No text'}, ${functionCalls.length} function calls`);
        }
        
        processSseEventData(JSON.stringify(event), aiMessageId);
      }

      setIsLoading(false);

    } catch (error) {
      console.error("Error:", error);
      const aiMessageId = Date.now().toString() + "_ai_error";
      setMessages(prev => [...prev, { 
        type: "ai", 
        content: `Sorry, there was an error processing your request: ${error instanceof Error ? error.message : 'Unknown error'}`, 
        id: aiMessageId 
      }]);
      setIsLoading(false);
    }
  }, [userId, sessionId, appName, processSseEventData]);

  const handleTrendSelection = useCallback(async (trendType: 'google' | 'youtube', trend: any) => {
    const trendMessage = trendType === 'google' 
      ? `select google trend: ${trend.name}`
      : `select youtube trend: ${trend.title}`;
    
    // Track the selection
    if (trendType === 'google') {
      setSelectedGoogleTrend(trend.name);
    } else {
      setSelectedYoutubeTrend(trend.title);
    }
    
    // Hide selector after both trends are selected
    if ((trendType === 'google' && selectedYoutubeTrend) || 
        (trendType === 'youtube' && selectedGoogleTrend)) {
      setTrendSelectorVisible(false);
    }
    
    await handleSubmit(trendMessage);
  }, [handleSubmit, selectedGoogleTrend, selectedYoutubeTrend]);

  const toggleTrendSelector = useCallback(() => {
    setTrendSelectorVisible(prev => !prev);
  }, []);

  useEffect(() => {
    if (scrollAreaRef.current) {
      const scrollViewport = scrollAreaRef.current.querySelector(
        "[data-radix-scroll-area-viewport]"
      );
      if (scrollViewport) {
        scrollViewport.scrollTo({
          top: scrollViewport.scrollHeight,
          behavior: 'smooth'
        });
      }
    }
  }, [messages, messageEvents, displayData, isLoading]);

  useEffect(() => {
    const checkBackend = async () => {
      setIsCheckingBackend(true);
      
      const maxAttempts = 60;
      let attempts = 0;
      
      while (attempts < maxAttempts) {
        const isReady = await checkBackendHealth();
        if (isReady) {
          setIsBackendReady(true);
          setIsCheckingBackend(false);
          return;
        }
        
        attempts++;
        await new Promise(resolve => setTimeout(resolve, 2000));
      }
      
      setIsCheckingBackend(false);
      console.error("Backend failed to start within 2 minutes");
    };
    
    checkBackend();
  }, []);

  const handleCancel = useCallback(() => {
    setMessages([]);
    setDisplayData(null);
    setMessageEvents(new Map());
    setSourceCount(0);
    setGoogleTrends([]);
    setYoutubeTrends([]);
    setCampaignData(null);
    setSelectedGoogleTrend(null);
    setSelectedYoutubeTrend(null);
    setTrendSelectorVisible(true);
    window.location.reload();
  }, []);

  const handleSessionChange = useCallback(async (newSessionId: string) => {
    // Clear current messages
    setMessages([]);
    setMessageEvents(new Map());
    setSourceCount(0);
    setGoogleTrends([]);
    setYoutubeTrends([]);
    setCampaignData(null);
    setDisplayData(null);
    setSelectedGoogleTrend(null);
    setSelectedYoutubeTrend(null);
    setTrendSelectorVisible(true);
    currentAgentRef.current = '';
    accumulatedTextRef.current = '';
    
    // Update session ID
    setSessionId(newSessionId);
    
    // Load messages for the new session
    if (userId && appName) {
      try {
        const response = await fetch(`/api/apps/${appName}/users/${userId}/sessions/${newSessionId}/messages`);
        if (response.ok) {
          const sessionData = await response.json();
          
          // Convert session messages to our format
          const loadedMessages: MessageWithAgent[] = [];
          if (sessionData && sessionData.messages) {
            sessionData.messages.forEach((msg: any) => {
              if (msg.role === 'user' && msg.content?.parts) {
                // Add user message
                const text = msg.content.parts.map((p: any) => p.text).join('');
                loadedMessages.push({
                  type: 'human',
                  content: text,
                  id: `loaded-${Date.now()}-${Math.random()}`,
                });
              } else if (msg.role === 'model' && msg.content?.parts) {
                // Add AI message
                const text = msg.content.parts.map((p: any) => p.text).join('');
                loadedMessages.push({
                  type: 'ai',
                  content: text,
                  id: `loaded-${Date.now()}-${Math.random()}`,
                  agent: msg.author || 'assistant',
                });
              }
            });
          }
          
          if (loadedMessages.length > 0) {
            setMessages(loadedMessages);
          }
        } else {
          // If no message history available, add an info message
          console.log(`Session switched to: ${newSessionId}`);
          setMessages([{
            type: 'system',
            content: `Session switched to: ${newSessionId}\n\nNote: Message history is not persisted. You can continue the conversation from here.`,
            id: `system-${Date.now()}`
          }]);
        }
      } catch (error) {
        console.error('Error loading session history:', error);
        // Add a message about the session switch
        setMessages([{
          type: 'system',
          content: `Session switched to: ${newSessionId}\n\nYou can start or continue your conversation.`,
          id: `system-${Date.now()}`
        }]);
      }
    }
  }, [userId, appName]);

  const BackendLoadingScreen = () => (
    <div className="flex-1 flex flex-col items-center justify-center p-4 relative">
      <div className="w-full max-w-2xl z-10
                      bg-neutral-900/50 backdrop-blur-md 
                      p-8 rounded-2xl border border-neutral-700 
                      shadow-2xl shadow-black/60">
        
        <div className="text-center space-y-6">
          <h1 className="text-4xl font-bold text-white flex items-center justify-center gap-3">
            🚀 Marketing Intelligence System
          </h1>
          
          <div className="flex flex-col items-center space-y-4">
            <div className="relative">
              <div className="w-16 h-16 border-4 border-neutral-600 border-t-blue-500 rounded-full animate-spin"></div>
              <div className="absolute inset-0 w-16 h-16 border-4 border-transparent border-r-purple-500 rounded-full animate-spin" style={{animationDirection: 'reverse', animationDuration: '1.5s'}}></div>
            </div>
            
            <div className="space-y-2">
              <p className="text-xl text-neutral-300">
                Waiting for backend to be ready...
              </p>
              <p className="text-sm text-neutral-400">
                This may take a moment on first startup
              </p>
            </div>
            
            <div className="flex space-x-1">
              <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{animationDelay: '0ms'}}></div>
              <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style={{animationDelay: '150ms'}}></div>
              <div className="w-2 h-2 bg-pink-500 rounded-full animate-bounce" style={{animationDelay: '300ms'}}></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="flex h-screen bg-neutral-800 text-neutral-100 font-sans antialiased">
      <main className="flex-1 flex flex-col w-full">
        <div className={`flex-1 ${(messages.length === 0 || isCheckingBackend) ? "flex" : ""}`}>
          {isCheckingBackend ? (
            <BackendLoadingScreen />
          ) : !isBackendReady ? (
            <div className="flex-1 flex flex-col items-center justify-center p-4">
              <div className="text-center space-y-4">
                <h2 className="text-2xl font-bold text-red-400">Backend Unavailable</h2>
                <p className="text-neutral-300">
                  Unable to connect to backend services at localhost:8000
                </p>
                <button 
                  onClick={() => window.location.reload()} 
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
                >
                  Retry
                </button>
              </div>
            </div>
          ) : messages.length === 0 ? (
            <WelcomeScreen
              handleSubmit={handleSubmit}
              isLoading={isLoading}
              onCancel={handleCancel}
              sessionId={sessionId}
              userId={userId}
              appName={appName}
              onSessionChange={handleSessionChange}
            />
          ) : (
            <ChatMessagesView
              messages={messages}
              isLoading={isLoading}
              scrollAreaRef={scrollAreaRef}
              onSubmit={handleSubmit}
              onCancel={handleCancel}
              displayData={displayData}
              messageEvents={messageEvents}
              sourceCount={sourceCount}
              googleTrends={googleTrends}
              youtubeTrends={youtubeTrends}
              sessionId={sessionId}
              userId={userId}
              appName={appName}
              campaignData={campaignData}
              onTrendSelect={handleTrendSelection}
              onSessionChange={handleSessionChange}
              selectedGoogleTrend={selectedGoogleTrend}
              selectedYoutubeTrend={selectedYoutubeTrend}
              trendSelectorVisible={trendSelectorVisible}
              onToggleTrendSelector={toggleTrendSelector}
            />
          )}
        </div>
      </main>
    </div>
  );
}