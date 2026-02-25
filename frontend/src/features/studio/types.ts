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

export interface StudioData {
  clips: Clip[];
  characters: Character[];
  commercial?: CommercialData;
  isLoading: boolean;
}
