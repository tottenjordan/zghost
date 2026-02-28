import { useState, useRef, useEffect, useCallback } from 'react';
import { Send, CheckCircle, XCircle, ChevronDown, Loader2 } from 'lucide-react';
import { api } from '../../services/api';
import { cn } from '../../lib/utils';
import type { AgentEvent } from '../../types/agents';

const USER_ID = 'default-user';

interface AgentChatProps {
  sessionId: string | null;
  events: AgentEvent[];
  onWaitingForInput?: (waiting: boolean) => void;
  onSendMessage?: (message: string) => void;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'agent';
  agent?: string;
  text: string;
  timestamp: number;
}

function extractChatMessages(events: AgentEvent[]): ChatMessage[] {
  const messages: ChatMessage[] = [];

  for (const event of events) {
    // Extract text from SSE event parts
    let text = '';
    if (event.data?.parts) {
      for (const part of event.data.parts) {
        if (part.text) text += part.text;
      }
    }
    // Fallback to legacy content field
    if (!text && event.data?.content && typeof event.data.content === 'string') {
      text = event.data.content;
    }

    if (!text || text.trim().length === 0) continue;

    // Skip tool calls and very short internal messages
    if (event.type === 'tool_call' || event.type === 'tool_response') continue;
    if (text.length < 10 && !text.includes('?')) continue;

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

export function AgentChat({ sessionId, events, onWaitingForInput, onSendMessage }: AgentChatProps) {
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const [lastApprovedTimestamp, setLastApprovedTimestamp] = useState<number>(0);
  const [isSending, setIsSending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const messages = extractChatMessages(events);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages.length, autoScroll]);

  const lastAgentMessage = messages.filter(m => m.role === 'agent').slice(-1)[0];

  // Clear isSending state when new agent message arrives
  useEffect(() => {
    if (lastAgentMessage) {
      setIsSending(false);
    }
  }, [lastAgentMessage?.timestamp]);

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
  const isWaitingForApproval = lastAgentMessage &&
    lastAgentMessage.timestamp > lastApprovedTimestamp &&
    (lastAgentMessage.text?.includes('?') ||
    lastAgentText.includes('approve') ||
    lastAgentText.includes('look good') ||
    lastAgentText.includes('proceed') ||
    lastAgentText.includes('select') ||
    lastAgentText.includes('choose') ||
    lastAgentText.includes('confirm') ||
    lastAgentText.includes('verify') ||
    lastAgentText.includes('provide') ||
    lastAgentText.includes('enter') ||
    lastAgentText.includes('specify') ||
    lastAgentText.includes('would you like') ||
    lastAgentText.includes('yes or no') ||
    lastAgentText.includes('ready to'));

  // Notify parent about input waiting state
  useEffect(() => {
    onWaitingForInput?.(isWaitingForApproval);
  }, [isWaitingForApproval, onWaitingForInput]);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-zinc-800 flex-shrink-0">
        <span className="text-sm font-medium text-zinc-300">Agent Chat</span>
        {isWaitingForApproval && (
          <span className="px-2 py-0.5 rounded text-xs bg-amber-950/50 border border-amber-800/50 text-amber-400 animate-pulse">
            Awaiting response
          </span>
        )}
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
              <div className="whitespace-pre-wrap text-xs leading-relaxed">
                {msg.text.length > 500
                  ? msg.text.slice(0, 500) + '...'
                  : msg.text}
              </div>
            </div>
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
