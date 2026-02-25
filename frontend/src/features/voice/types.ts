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

export interface VoiceSessionConfig {
  systemPrompt: string;
  wsUrl?: string;
  voiceConfig?: {
    sampleRate?: number;
    channels?: number;
  };
}
