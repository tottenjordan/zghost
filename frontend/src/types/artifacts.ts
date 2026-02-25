export type ArtifactType = 'image' | 'video' | 'commercial' | 'report';

export interface Artifact {
  id: string;
  type: ArtifactType;
  url: string;
  gcsKey?: string;
  metadata?: Record<string, any>;
  createdAt?: string;
}

export interface ImageArtifact extends Artifact {
  type: 'image';
  width?: number;
  height?: number;
  prompt?: string;
}

export interface VideoArtifact extends Artifact {
  type: 'video';
  duration?: number;
  prompt?: string;
}

export interface CommercialArtifact extends Artifact {
  type: 'commercial';
  duration: number;
  scenes?: Array<{
    startTime: number;
    endTime: number;
    description: string;
  }>;
}
