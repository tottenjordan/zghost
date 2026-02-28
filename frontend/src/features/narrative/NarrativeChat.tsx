import { useState, useRef, useEffect } from 'react';
import type { Message } from './types';
import { Button } from '../../components/ui/Button';
import { Spinner } from '../../components/ui/Spinner';
import { Markdown } from '../../components/ui/Markdown';

interface NarrativeChatProps {
  messages: Message[];
  isStreaming: boolean;
  onSendMessage: (content: string) => void;
}

const QUICK_ACTIONS = [
  { label: 'More dramatic', prompt: 'Make the narrative more dramatic and intense' },
  { label: 'Lighter tone', prompt: 'Adjust to a lighter, more upbeat tone' },
  { label: 'Add humor', prompt: 'Add some humor to the commercial' },
  { label: 'Focus on product', prompt: 'Focus more on the product features' },
  { label: 'Extend climax', prompt: 'Extend the climax scene for more impact' },
];

export function NarrativeChat({
  messages,
  isStreaming,
  onSendMessage,
}: NarrativeChatProps) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const prevMsgCount = useRef(messages.length);

  // Auto-scroll only when new messages arrive AND user hasn't scrolled up
  useEffect(() => {
    if (messages.length > prevMsgCount.current && autoScroll) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
    prevMsgCount.current = messages.length;
  }, [messages.length, autoScroll]);

  // Scroll to bottom on initial load only
  useEffect(() => {
    if (messages.length > 0) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'instant' });
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !isStreaming) {
      onSendMessage(input.trim());
      setInput('');
    }
  };

  const handleQuickAction = (prompt: string) => {
    if (!isStreaming) {
      onSendMessage(prompt);
    }
  };

  return (
    <div className="flex h-full flex-col rounded-lg border border-zinc-800 bg-zinc-900">
      {/* Header */}
      <div className="border-b border-zinc-800 p-4">
        <h3 className="text-lg font-semibold text-zinc-100">
          Narrative Director
        </h3>
        <p className="text-xs text-zinc-500">
          Chat with the AI to refine your commercial's story
        </p>
      </div>

      {/* Messages */}
      <div
        ref={scrollContainerRef}
        className="flex-1 overflow-y-auto p-4"
        onScroll={() => {
          const el = scrollContainerRef.current;
          if (el) {
            const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 60;
            setAutoScroll(atBottom);
          }
        }}
      >
        {messages.length === 0 ? (
          <div className="flex h-full items-center justify-center">
            <div className="text-center">
              <p className="mb-2 text-zinc-400">No messages yet</p>
              <p className="text-xs text-zinc-600">
                Start a conversation about your commercial narrative
              </p>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[80%] rounded-lg px-4 py-2 ${
                    message.role === 'user'
                      ? 'bg-blue-600 text-white'
                      : 'bg-zinc-800 text-zinc-100'
                  }`}
                >
                  {message.role === 'assistant' ? (
                    <Markdown content={message.content} />
                  ) : (
                    <p className="whitespace-pre-wrap text-sm">{message.content}</p>
                  )}

                  {/* Media Preview */}
                  {message.mediaPreview && (
                    <div className="mt-2">
                      {message.mediaPreview.type === 'image' ? (
                        <img
                          src={message.mediaPreview.url}
                          alt={message.mediaPreview.caption || 'Preview'}
                          className="max-h-48 rounded border border-zinc-700"
                        />
                      ) : (
                        <video
                          src={message.mediaPreview.url}
                          controls
                          className="max-h-48 rounded border border-zinc-700"
                        />
                      )}
                      {message.mediaPreview.caption && (
                        <p className="mt-1 text-xs text-zinc-400">
                          {message.mediaPreview.caption}
                        </p>
                      )}
                    </div>
                  )}

                  <span className="mt-1 block text-xs opacity-60">
                    {new Date(message.timestamp).toLocaleTimeString()}
                  </span>
                </div>
              </div>
            ))}

            {isStreaming && (
              <div className="flex justify-start">
                <div className="flex items-center gap-2 rounded-lg bg-zinc-800 px-4 py-2">
                  <Spinner size="sm" />
                  <span className="text-sm text-zinc-400">Thinking...</span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="border-t border-zinc-800 p-3">
        <div className="mb-2 flex flex-wrap gap-2">
          {QUICK_ACTIONS.map((action) => (
            <button
              key={action.label}
              onClick={() => handleQuickAction(action.prompt)}
              disabled={isStreaming}
              className="rounded-full bg-zinc-800 px-3 py-1 text-xs text-zinc-300 transition-colors hover:bg-zinc-700 disabled:opacity-50"
            >
              {action.label}
            </button>
          ))}
        </div>
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="border-t border-zinc-800 p-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Describe your vision for the commercial..."
            disabled={isStreaming}
            className="flex-1 rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2 text-sm text-zinc-100 placeholder-zinc-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-50"
          />
          <Button
            type="submit"
            variant="primary"
            size="md"
            disabled={!input.trim() || isStreaming}
          >
            Send
          </Button>
        </div>
      </form>
    </div>
  );
}
