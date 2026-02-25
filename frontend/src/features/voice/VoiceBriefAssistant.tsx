import { useState, useEffect } from 'react';
import { Mic, MicOff, X, Volume2 } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { AudioVisualizer } from './AudioVisualizer';
import { useVoiceSession } from './useVoiceSession';
import { VoiceCommandRouter } from './VoiceCommandRouter';
import type { ConnectionState } from './types';
import { cn } from '../../lib/utils';

const SYSTEM_PROMPT = `You are a helpful marketing brief refinement assistant. Your role is to help users refine their marketing campaign briefs before creative ideation begins.

Ask clarifying questions about:
- Target audience and demographics
- Campaign goals and KPIs
- Brand voice and messaging guidelines
- Budget and timeline constraints
- Key messaging pillars
- Competitive landscape

Be conversational, concise, and focus on gathering the essential information needed for a strong creative brief. Help users think through aspects they might have missed.`;

interface VoiceBriefAssistantProps {
  onClose?: () => void;
  isFloating?: boolean;
}

export function VoiceBriefAssistant({ onClose, isFloating = false }: VoiceBriefAssistantProps) {
  const [isMinimized, setIsMinimized] = useState(false);

  const {
    connectionState,
    transcript,
    error,
    toggleRecording,
    disconnect,
    isRecording,
    isConnected,
  } = useVoiceSession({
    systemPrompt: SYSTEM_PROMPT,
  });

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  const getStatusColor = (state: ConnectionState): 'default' | 'success' | 'warning' | 'info' | 'error' => {
    switch (state) {
      case 'connected':
      case 'listening':
        return 'success';
      case 'connecting':
      case 'processing':
        return 'info';
      case 'speaking':
        return 'warning';
      case 'error':
        return 'error';
      default:
        return 'default';
    }
  };

  const getStatusText = (state: ConnectionState): string => {
    switch (state) {
      case 'idle':
        return 'Ready to connect';
      case 'connecting':
        return 'Connecting...';
      case 'connected':
        return 'Connected';
      case 'listening':
        return 'Listening...';
      case 'processing':
        return 'Processing...';
      case 'speaking':
        return 'Speaking...';
      case 'error':
        return 'Error';
      default:
        return 'Unknown';
    }
  };

  if (isMinimized && isFloating) {
    return (
      <div className="fixed bottom-4 right-4 z-50">
        <Button
          onClick={() => setIsMinimized(false)}
          className="h-14 w-14 rounded-full shadow-lg"
          variant="primary"
        >
          <Mic className="h-6 w-6" />
        </Button>
      </div>
    );
  }

  return (
    <>
      {/* Voice Command Router - renders notification when commands are detected */}
      <VoiceCommandRouter transcript={transcript} />

      <Card
        className={cn(
          'flex flex-col overflow-hidden',
          isFloating
            ? 'fixed bottom-4 right-4 z-50 w-[400px] h-[600px] shadow-2xl'
            : 'h-full'
        )}
      >
        <CardHeader className="border-b border-zinc-800 bg-zinc-900/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <CardTitle className="text-lg">Voice Brief Assistant</CardTitle>
            <Badge variant={getStatusColor(connectionState)}>
              {getStatusText(connectionState)}
            </Badge>
          </div>
          <div className="flex items-center gap-2">
            {isFloating && (
              <>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setIsMinimized(true)}
                  className="h-7 w-7 p-0"
                >
                  <MicOff className="h-4 w-4" />
                </Button>
                {onClose && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={onClose}
                    className="h-7 w-7 p-0"
                  >
                    <X className="h-4 w-4" />
                  </Button>
                )}
              </>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="flex flex-1 flex-col gap-4 overflow-hidden p-6">
        {/* Error message */}
        {error && (
          <div className="rounded-lg border border-red-800 bg-red-950/50 px-3 py-2 text-sm text-red-300">
            {error}
          </div>
        )}

        {/* Audio visualizer */}
        <div className="h-24 rounded-lg border border-zinc-800 bg-zinc-950 overflow-hidden">
          <AudioVisualizer
            isActive={isRecording || connectionState === 'speaking'}
            isSpeaking={connectionState === 'speaking'}
            className="h-full"
          />
        </div>

        {/* Transcript */}
        <div className="flex-1 space-y-3 overflow-y-auto rounded-lg border border-zinc-800 bg-zinc-950 p-4">
          {transcript.length === 0 ? (
            <div className="flex h-full items-center justify-center text-center text-sm text-zinc-500">
              <div>
                <Volume2 className="mx-auto mb-2 h-8 w-8 opacity-50" />
                <p>Click the microphone to start your voice conversation</p>
                <p className="mt-1 text-xs">
                  I'll help you refine your campaign brief
                </p>
              </div>
            </div>
          ) : (
            transcript.map((message) => (
              <div
                key={message.id}
                className={cn(
                  'rounded-lg px-3 py-2 text-sm',
                  message.role === 'user'
                    ? 'ml-8 bg-blue-600/20 text-blue-100'
                    : 'mr-8 bg-zinc-800/50 text-zinc-200'
                )}
              >
                <div className="mb-1 text-xs font-medium text-zinc-400">
                  {message.role === 'user' ? 'You' : 'Assistant'}
                </div>
                <div>{message.content}</div>
              </div>
            ))
          )}
        </div>

        {/* Controls */}
        <div className="flex gap-3">
          <Button
            onClick={toggleRecording}
            disabled={connectionState === 'error'}
            className={cn(
              'flex-1 relative overflow-hidden transition-all duration-300',
              isRecording && 'ring-2 ring-blue-400 ring-offset-2 ring-offset-zinc-950'
            )}
            variant={isRecording ? 'primary' : 'secondary'}
          >
            {isRecording && (
              <span className="absolute inset-0 animate-pulse bg-blue-400/20" />
            )}
            <span className="relative flex items-center justify-center gap-2">
              {isRecording ? (
                <>
                  <MicOff className="h-5 w-5" />
                  Stop Recording
                </>
              ) : (
                <>
                  <Mic className="h-5 w-5" />
                  {isConnected ? 'Start Recording' : 'Connect & Record'}
                </>
              )}
            </span>
          </Button>

          {isConnected && (
            <Button
              onClick={disconnect}
              variant="ghost"
              className="px-4"
            >
              Disconnect
            </Button>
          )}
        </div>

        {/* Instructions */}
        {!isConnected && (
          <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 px-3 py-2 text-xs text-zinc-400">
            <p className="font-medium text-zinc-300 mb-1">How it works:</p>
            <ul className="space-y-1 list-disc list-inside">
              <li>Click "Connect & Record" to start</li>
              <li>Speak naturally about your campaign</li>
              <li>The assistant will ask clarifying questions</li>
              <li>Stop recording when finished</li>
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
    </>
  );
}
