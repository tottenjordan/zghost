export interface Clip {
  id: string;
  name: string;
  sceneDescription: string;
  duration: number;
  order: number;
  gcsUri: string;
  url: string;
  status: 'generating' | 'ready' | 'error';
  thumbnailUrl?: string;
  firstFrameUrl?: string;
  lastFrameUrl?: string;
  generationParams?: {
    prompt: string;
    firstFrameGcsUri?: string;
    lastFrameGcsUri?: string;
  };
  error?: string;
}

export interface Character {
  id: string;
  name: string;
  imageUrl: string;
  gcsUri: string;
  usageCount: number;
  description?: string;
}

export interface CommercialData {
  url: string;
  gcsUri: string;
  duration: number;
  title: string;
  narrativeArc?: string;
  targetAudience?: string;
  trendConnections?: string;
  scenes?: Array<{
    startTime: number;
    endTime: number;
    description: string;
  }>;
}

// Voice configuration matching backend CHIRP_VOICES
export type VoiceStyleId =
  | 'professional_male'
  | 'professional_female'
  | 'energetic_male'
  | 'warm_female'
  | 'british_male'
  | 'british_female';

export interface VoiceStyle {
  id: VoiceStyleId;
  name: string;
  languageCode: string;
  description: string;
}

export interface VoiceConfig {
  style: VoiceStyleId;
  speakingRate: number;  // 0.5 - 2.0
  pitch: number;         // -10.0 to +10.0
  script?: string;
}

// Music configuration matching backend Lyria integration
export interface MusicConfig {
  prompt: string;
  durationSeconds: number;
  genre: string;
  mood: string;
  instruments: string;
}

export interface MusicSample {
  id: string;
  name: string;
  genre: string;
  mood: string;
  instruments: string;
  prompt: string;
  durationSeconds: number;
  gcsUri?: string;
  url?: string;
  status: 'pending' | 'generating' | 'ready' | 'error';
  error?: string;
}

export interface VoiceSample {
  id: string;
  label: string;
  style: VoiceStyleId;
  speakingRate: number;
  pitch: number;
  script: string;
  gcsUri?: string;
  url?: string;
  status: 'pending' | 'generating' | 'ready' | 'error';
  error?: string;
}

export interface AudioTrack {
  id: string;
  musicSampleId: string;
  name: string;
  url?: string;
  gcsUri?: string;
  startTime: number;    // offset in seconds on the timeline
  duration: number;     // duration in seconds
}

export interface StudioData {
  clips: Clip[];
  characters: Character[];
  commercial?: CommercialData;
  voiceSamples: VoiceSample[];
  musicSamples: MusicSample[];
  audioTracks: AudioTrack[];
  selectedVoice: VoiceStyleId | null;
  selectedMusic: string | null;  // MusicSample id
  isLoading: boolean;
}
