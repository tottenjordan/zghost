import { useState, useRef, useEffect, useCallback } from 'react';
import { Send, CheckCircle, XCircle, ChevronDown } from 'lucide-react';
import { api } from '../../services/api';
import { cn } from '../../lib/utils';
import type { AgentEvent } from '../../types/agents';

const APP_NAME = import.meta.env.VITE_APP_NAME || 'trends_and_insights_agent';
const USER_ID = 'frontend-user';

interface AgentChatProps {
  sessionId: string | null;
  events: AgentEvent[];
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
    const text = event.data?.content;
    if (!text || typeof text !== 'string' || text.trim().length === 0) continue;

    // Skip very short internal messages and tool calls
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

  return messages;
}

export function AgentChat({ sessionId, events }: AgentChatProps) {
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const messages = extractChatMessages(events);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages.length, autoScroll]);

  const handleSend = useCallback(async (text: string) => {
    if (!sessionId || !text.trim() || sending) return;

    setSending(true);
    try {
      await api.sendMessage({
        app_name: APP_NAME,
        user_id: USER_ID,
        session_id: sessionId,
        message: text.trim(),
      });
      setInput('');
    } catch (err) {
      console.error('Failed to send message:', err);
    } finally {
      setSending(false);
      inputRef.current?.focus();
    }
  }, [sessionId, sending]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend(input);
    }
  };

  const lastAgentMessage = messages.filter(m => m.role === 'agent').slice(-1)[0];
  const isWaitingForApproval = lastAgentMessage?.text?.includes('?') ||
    lastAgentMessage?.text?.toLowerCase().includes('approve') ||
    lastAgentMessage?.text?.toLowerCase().includes('look good') ||
    lastAgentMessage?.text?.toLowerCase().includes('proceed');

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
            onClick={() => handleSend('Looks good, proceed with all options.')}
            disabled={sending}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-green-600/20 border border-green-700/50 text-green-400 text-xs font-medium hover:bg-green-600/30 disabled:opacity-50"
          >
            <CheckCircle className="w-3.5 h-3.5" />
            Approve All
          </button>
          <button
            onClick={() => handleSend('Please revise and try again with improvements.')}
            disabled={sending}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-red-600/10 border border-red-700/50 text-red-400 text-xs font-medium hover:bg-red-600/20 disabled:opacity-50"
          >
            <XCircle className="w-3.5 h-3.5" />
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
