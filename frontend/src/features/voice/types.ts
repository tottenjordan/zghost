export type ConnectionState =
  | 'idle'
  | 'connecting'
  | 'connected'
  | 'listening'
  | 'processing'
  | 'speaking'
  | 'error';

export interface TranscriptMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
}

export interface VoiceAction {
  type: 'action';
  action: string;
  params?: Record<string, any>;
}

export interface VoiceSessionConfig {
  systemPrompt: string;
  onAction?: (action: VoiceAction) => void;
  wsUrl?: string;
  voiceConfig?: {
    sampleRate?: number;
    channels?: number;
  };
}
