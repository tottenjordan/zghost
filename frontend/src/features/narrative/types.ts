export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
  mediaPreview?: {
    type: 'image' | 'video';
    url: string;
    caption?: string;
  };
}

export interface Scene {
  id: string;
  order: number;
  sceneNumber: number;
  description: string;
  duration: number;
  frameUrl?: string;
  narrativeBeat: 'setup' | 'rising_action' | 'climax' | 'resolution';
  prompt?: string;
}

export interface NarrativeArc {
  setup: string;
  risingAction: string;
  climax: string;
  resolution: string;
}

export interface NarrativeData {
  messages: Message[];
  scenes: Scene[];
  narrativeArc?: NarrativeArc;
  isStreaming: boolean;
}
