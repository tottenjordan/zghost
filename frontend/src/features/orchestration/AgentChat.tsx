import { useState, useRef, useEffect, useCallback } from 'react';
import { Send, CheckCircle, XCircle, ChevronDown, Loader2, FileText, ArrowRight, Film } from 'lucide-react';
import { Link } from 'react-router-dom';
import { api, gcsToProxyUrl } from '../../services/api';
import { cn } from '../../lib/utils';
import type { AgentEvent } from '../../types/agents';

/** Render text with clickable GCS links (PDF → Narrative, media → AV Studio) */
function RichText({ text, sessionId }: { text: string; sessionId?: string | null }) {
  // Match gs:// URLs
  const gcsPattern = /gs:\/\/[^\s)]+/g;
  const parts: (string | JSX.Element)[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = gcsPattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    const url = match[0];
    const isPdf = url.endsWith('.pdf');
    const isMedia = /\.(mp4|webm|mov|png|jpg|jpeg|gif|webp|mp3|wav)$/i.test(url);

    if (isPdf && sessionId) {
      parts.push(
        <Link
          key={match.index}
          to={`/narrative?session=${sessionId}`}
          className="inline-flex items-center gap-1 text-blue-400 hover:text-blue-300 underline underline-offset-2"
        >
          <FileText className="w-3 h-3 inline" />
          View in Narrative Studio
        </Link>
      );
    } else if (isMedia) {
      const studioPath = sessionId ? `/studio?session=${sessionId}` : '/studio';
      parts.push(
        <Link
          key={match.index}
          to={studioPath}
          className="inline-flex items-center gap-1 text-green-400 hover:text-green-300 underline underline-offset-2"
        >
          <Film className="w-3 h-3 inline" />
          {url.split('/').pop()}
        </Link>
      );
    } else {
      const httpUrl = gcsToProxyUrl(url);
      parts.push(
        <a
          key={match.index}
          href={httpUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="text-blue-400 hover:text-blue-300 underline underline-offset-2"
        >
          {url.split('/').pop()}
        </a>
      );
    }
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return <>{parts}</>;
}

const USER_ID = 'default-user';

interface AgentChatProps {
  sessionId: string | null;
  events: AgentEvent[];
  autopilot?: boolean;
  onWaitingForInput?: (waiting: boolean) => void;
  onSendMessage?: (message: string) => void;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'agent' | 'status';
  agent?: string;
  text: string;
  timestamp: number;
}

/** Friendly labels for internal tool/agent names */
const TOOL_LABELS: Record<string, string> = {
  transfer_to_agent: '',  // skip — not user-facing
  load_skill: '',         // skip — internal
  combined_research_pipeline: 'Starting market research pipeline...',
  research_orchestrator: 'Handing off to Research Orchestrator',
  ad_content_generator_agent: 'Starting ad creative generation...',
  ad_creative_pipeline: 'Drafting ad copy...',
  visual_generation_pipeline: 'Creating visual concepts...',
  visual_generator: 'Generating images & videos...',
  generate_visuals_batch: 'Generating visuals in parallel...',
  generate_image: 'Generating image...',
  generate_video: 'Generating video...',
  generate_subject_image: 'Generating product image...',
  generate_clips_parallel: 'Generating video clips in parallel...',
  generate_clip_with_frames: 'Generating video clip...',
  av_editing_studio_agent: 'Starting AV commercial production...',
  focus_group_evaluator_agent: 'Running focus group evaluation...',
  trends_and_insights_agent: 'Starting trend discovery...',
};

function extractChatMessages(events: AgentEvent[]): ChatMessage[] {
  const messages: ChatMessage[] = [];

  for (const event of events) {
    // Extract text from SSE event parts
    let text = '';
    let toolCallName = '';
    if (event.data?.parts) {
      for (const part of event.data.parts) {
        if (part.text) text += part.text;
        if (part.function_call?.name) toolCallName = part.function_call.name;
      }
    }
    // Fallback to legacy content field
    if (!text && event.data?.content && typeof event.data.content === 'string') {
      text = event.data.content;
    }

    // Generate status message from tool_call events
    if (!text && event.type === 'tool_call' && toolCallName) {
      const label = TOOL_LABELS[toolCallName];
      if (label === '') continue;  // explicitly skipped
      const statusText = label || `Running ${toolCallName.replace(/_/g, ' ')}...`;
      messages.push({
        id: `${event.timestamp}-${event.agentName}-${toolCallName}`,
        role: 'status',
        agent: event.agentName,
        text: statusText,
        timestamp: event.timestamp,
      });
      continue;
    }

    if (!text || text.trim().length === 0) continue;

    // Skip tool responses entirely; for tool_calls, only skip if no text
    if (event.type === 'tool_response') continue;
    if (event.type === 'tool_call' && !text) continue;
    if (text.length < 10 && !text.includes('?')) continue;

    // Filter out short sub-agent routing messages (e.g. "Starting ad copy...",
    // "Ad Copy completed."). Only show substantial content from sub-agents.
    const isRootOrUser = event.agentName === 'root_agent' || event.agentName === 'user';
    if (!isRootOrUser && text.length < 120) continue;

    const isUser = event.agentName === 'user';
    messages.push({
      id: `${event.timestamp}-${event.agentName}`,
      role: isUser ? 'user' : 'agent',
      agent: isUser ? undefined : event.agentName,
      text: text.slice(0, 2000),
      timestamp: event.timestamp,
    });
  }

  return deduplicateMessages(messages);
}

function deduplicateMessages(messages: ChatMessage[]): ChatMessage[] {
  const deduplicated: ChatMessage[] = [];
  let lastUserMessage: ChatMessage | null = null;

  for (const msg of messages) {
    if (msg.role === 'user') {
      // Skip if same text as previous user message within 5 seconds
      if (
        lastUserMessage &&
        lastUserMessage.text === msg.text &&
        msg.timestamp - lastUserMessage.timestamp < 5000
      ) {
        continue;
      }
      lastUserMessage = msg;
    }
    deduplicated.push(msg);
  }

  return deduplicated;
}

export function AgentChat({ sessionId, events, autopilot, onWaitingForInput, onSendMessage }: AgentChatProps) {
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const [lastApprovedTimestamp, setLastApprovedTimestamp] = useState<number>(0);
  const [isSending, setIsSending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const messages = extractChatMessages(events);

  // Scroll to bottom on mount and when new messages arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages.length, autoScroll]);

  const lastAgentMessage = messages.filter(m => m.role === 'agent').slice(-1)[0];

  // Clear isSending state when new agent message arrives or events change
  useEffect(() => {
    if (lastAgentMessage) {
      setIsSending(false);
    }
  }, [lastAgentMessage?.timestamp]);
  // Fallback: clear isSending when event count changes (covers filtered messages)
  useEffect(() => {
    if (isSending && events.length > 0) {
      setIsSending(false);
    }
  }, [events.length]);

  const sendingRef = useRef(false);

  const handleSend = useCallback(async (text: string, isApprovalAction = false) => {
    if (!sessionId || !text.trim() || sending || sendingRef.current) return;

    sendingRef.current = true;
    setSending(true);
    setIsSending(true);

    // Track approval timestamp to prevent button from re-appearing
    if (isApprovalAction) {
      setLastApprovedTimestamp(Date.now());
    }

    try {
      if (onSendMessage) {
        // Route through shared EventSource so events reach timeline/graph
        onSendMessage(text.trim());
      } else {
        // Fallback: consume events privately
        await api.sendMessage(sessionId, text.trim(), USER_ID);
      }
      setInput('');
    } catch (err) {
      console.error('Failed to send message:', err);
    } finally {
      sendingRef.current = false;
      setSending(false);
      // Don't clear isSending immediately - wait for new agent message
      inputRef.current?.focus();
    }
  }, [sessionId, sending, onSendMessage]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend(input);
    }
  };

  const lastAgentText = lastAgentMessage?.text?.toLowerCase() || '';
  const hasQuestionMark = lastAgentMessage?.text?.includes('?') || false;
  const isWaitingForApproval = lastAgentMessage &&
    lastAgentMessage.timestamp > lastApprovedTimestamp &&
    // Must have a question mark, or contain a clear prompt phrase
    (hasQuestionMark ||
    lastAgentText.includes('would you like') ||
    lastAgentText.includes('yes or no') ||
    lastAgentText.includes('ready to') ||
    lastAgentText.includes('look good') ||
    lastAgentText.includes('please approve') ||
    lastAgentText.includes('please confirm') ||
    lastAgentText.includes('please select') ||
    lastAgentText.includes('please choose'));

  // Notify parent about input waiting state
  useEffect(() => {
    onWaitingForInput?.(isWaitingForApproval);
  }, [isWaitingForApproval, onWaitingForInput]);

  // Autopilot: auto-send approval after 3s delay
  // Only guard with `sending` (not isSending) to avoid stuck states
  const autopilotTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    if (autopilot && isWaitingForApproval && !sending) {
      autopilotTimerRef.current = setTimeout(() => {
        handleSend('Approved. Continue to the next pipeline step without pausing for confirmation.', true);
      }, 3000);
    }
    return () => {
      if (autopilotTimerRef.current) clearTimeout(autopilotTimerRef.current);
    };
  }, [autopilot, isWaitingForApproval, sending, handleSend]);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-zinc-800 flex-shrink-0">
        <span className="text-sm font-medium text-zinc-300">Agent Chat</span>
        <div className="flex items-center gap-2">
          {autopilot && (
            <span className="px-2 py-0.5 rounded text-xs bg-blue-950/50 border border-blue-800/50 text-blue-400">
              {isWaitingForApproval ? 'Autopilot: auto-approving...' : 'Autopilot ON'}
            </span>
          )}
          {sessionId && (
            <Link
              to={`/narrative?session=${sessionId}`}
              className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 transition-colors"
            >
              <FileText className="w-3 h-3" />
              Open in Narrative
            </Link>
          )}
          {isWaitingForApproval && !autopilot && (
            <span className="px-2 py-0.5 rounded text-xs bg-amber-950/50 border border-amber-800/50 text-amber-400 animate-pulse">
              Awaiting response
            </span>
          )}
        </div>
      </div>

      {/* Messages */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-3 space-y-3"
        onScroll={(e) => {
          const el = e.currentTarget;
          const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
          setAutoScroll(atBottom);
        }}
      >
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full text-zinc-500 text-sm">
            Start the pipeline to see agent messages
          </div>
        ) : (
          messages.map((msg) => (
            msg.role === 'status' ? (
              <div
                key={msg.id}
                className="flex items-center gap-2 px-3 py-1.5 text-xs text-zinc-500"
              >
                <ArrowRight className="w-3 h-3 text-blue-500 flex-shrink-0" />
                <span className="font-medium text-zinc-400">{msg.agent}</span>
                <span>{msg.text}</span>
              </div>
            ) : (
              <div
                key={msg.id}
                className={cn(
                  'rounded-lg px-3 py-2 text-sm max-w-[95%]',
                  msg.role === 'user'
                    ? 'ml-auto bg-blue-600/20 text-blue-100 border border-blue-800/30'
                    : 'bg-zinc-800/50 text-zinc-200 border border-zinc-700/30'
                )}
              >
                {msg.agent && (
                  <div className="text-xs font-medium text-zinc-500 mb-1">
                    {msg.agent}
                  </div>
                )}
                <div className="whitespace-pre-wrap break-words overflow-wrap-anywhere text-xs leading-relaxed">
                  <RichText
                    text={msg.text.length > 500 ? msg.text.slice(0, 500) + '...' : msg.text}
                    sessionId={sessionId}
                  />
                </div>
              </div>
            )
          ))
        )}

        {!autoScroll && messages.length > 0 && (
          <button
            onClick={() => {
              setAutoScroll(true);
              scrollRef.current?.scrollTo({
                top: scrollRef.current.scrollHeight,
                behavior: 'smooth',
              });
            }}
            className="sticky bottom-0 mx-auto flex items-center gap-1 px-3 py-1 rounded-full bg-zinc-800 border border-zinc-700 text-xs text-zinc-400 hover:text-zinc-200"
          >
            <ChevronDown className="w-3 h-3" />
            Scroll to bottom
          </button>
        )}
      </div>

      {/* Quick actions */}
      {sessionId && isWaitingForApproval && (
        <div className="flex gap-2 px-3 py-2 border-t border-zinc-800/50">
          <button
            onClick={() => handleSend('Looks good, proceed with all options.', true)}
            disabled={sending || isSending}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-green-600/20 border border-green-700/50 text-green-400 text-xs font-medium hover:bg-green-600/30 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSending ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <CheckCircle className="w-3.5 h-3.5" />
            )}
            Approve All
          </button>
          <button
            onClick={() => handleSend('Please revise and try again with improvements.', true)}
            disabled={sending || isSending}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-red-600/10 border border-red-700/50 text-red-400 text-xs font-medium hover:bg-red-600/20 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSending ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <XCircle className="w-3.5 h-3.5" />
            )}
            Revise
          </button>
        </div>
      )}

      {/* Input */}
      {sessionId && (
        <div className="flex items-center gap-2 p-3 border-t border-zinc-800 flex-shrink-0">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Reply to the agent..."
            disabled={sending || !sessionId}
            className="flex-1 px-3 py-2 bg-zinc-900 border border-zinc-700 rounded text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-50"
          />
          <button
            onClick={() => handleSend(input)}
            disabled={sending || !input.trim()}
            className="p-2 rounded bg-blue-600 hover:bg-blue-700 disabled:bg-zinc-700 disabled:cursor-not-allowed text-white transition-colors"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
}
