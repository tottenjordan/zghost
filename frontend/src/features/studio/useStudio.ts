import { useState, useEffect } from 'react';
import { api } from '../../services/api';
import type { SessionState } from '../../types/session';
import type { Clip, Character, CommercialData, StudioData, VoiceSample, MusicSample, VoiceStyleId } from './types';

const BUCKET = import.meta.env.VITE_GCS_BUCKET || 'zghost-bucket';

function buildArtifactUrl(gcsFolder: string, artifactKey: string): string {
  return `https://storage.googleapis.com/${BUCKET}/${gcsFolder}/av_studio/${artifactKey}`;
}

function parseClipsFromState(
  vidArtifactKeys: string[],
  gcsFolder: string
): Clip[] {
  return vidArtifactKeys.map((key, index) => {
    const filename = key.split('/').pop() || key;
    const nameMatch = filename.match(/^(.+?)_[a-f0-9]{8}\.mp4$/);
    const clipName = nameMatch ? nameMatch[1] : filename.replace('.mp4', '');

    return {
      id: key,
      name: clipName,
      sceneDescription: `Scene ${index + 1}`,
      duration: 8,
      order: index,
      gcsUri: `gs://${BUCKET}/${key}`,
      url: buildArtifactUrl(gcsFolder, key.replace(`${gcsFolder}/av_studio/`, '')),
      status: 'ready' as const,
    };
  });
}

function parseCharactersFromState(
  imgArtifactKeys: string[],
  gcsFolder: string
): Character[] {
  return imgArtifactKeys
    .filter((key) => key.includes('/av_studio/subjects/'))
    .map((key) => {
      const filename = key.split('/').pop() || key;
      const nameMatch = filename.match(/^(.+?)_[a-f0-9]{8}\./);
      const characterName = nameMatch
        ? nameMatch[1].replace(/_/g, ' ')
        : filename;

      return {
        id: key,
        name: characterName,
        imageUrl: buildArtifactUrl(gcsFolder, key.replace(`${gcsFolder}/av_studio/`, '')),
        gcsUri: `gs://${BUCKET}/${key}`,
        usageCount: 1,
      };
    });
}

function parseCommercialFromState(
  commercialArtifact: any,
  gcsFolder: string
): CommercialData | undefined {
  if (!commercialArtifact) return undefined;

  const artifactKey =
    typeof commercialArtifact === 'string'
      ? commercialArtifact
      : commercialArtifact.artifact_key;
  const metadata =
    typeof commercialArtifact === 'object' ? commercialArtifact.metadata : {};

  return {
    url:
      typeof commercialArtifact === 'object' && commercialArtifact.gcs_uri
        ? buildArtifactUrl(gcsFolder, commercialArtifact.gcs_uri.split('/').pop())
        : buildArtifactUrl(gcsFolder, artifactKey),
    gcsUri:
      typeof commercialArtifact === 'object' && commercialArtifact.gcs_uri
        ? commercialArtifact.gcs_uri
        : `gs://${BUCKET}/${gcsFolder}/av_studio/${artifactKey}`,
    duration: metadata?.duration_seconds || 30,
    title: metadata?.title || 'Commercial',
    narrativeArc: metadata?.narrative_arc,
    targetAudience: metadata?.target_audience_appeal,
    trendConnections: metadata?.trend_connections,
    scenes: metadata?.scene_descriptions
      ? metadata.scene_descriptions.map((desc: string, idx: number) => ({
          startTime: idx * 7.5,
          endTime: (idx + 1) * 7.5,
          description: desc,
        }))
      : undefined,
  };
}

export function useStudio(sessionId: string | null) {
  const [studioData, setStudioData] = useState<StudioData>({
    clips: [],
    characters: [],
    commercial: undefined,
    voiceSamples: [],
    musicSamples: [],
    selectedVoice: null,
    selectedMusic: null,
    isLoading: false,
  });

  useEffect(() => {
    if (!sessionId) return;

    const fetchStudioData = async () => {
      setStudioData((prev) => ({ ...prev, isLoading: true }));

      try {
        const result = await api.getSessionState(sessionId, 'default-user');
        const state = result.state as SessionState;
        const gcsFolder = state.gcs_folder || 'default';

        const vidKeys = state.vid_artifact_keys?.vid_artifact_keys || [];
        const imgKeys = state.img_artifact_keys?.img_artifact_keys || [];
        const commercial = state.commercial_artifact;

        const clips = parseClipsFromState(vidKeys, gcsFolder);
        const characters = parseCharactersFromState(imgKeys, gcsFolder);
        const commercialData = parseCommercialFromState(commercial, gcsFolder);

        setStudioData({
          clips,
          characters,
          commercial: commercialData,
          isLoading: false,
        });
      } catch (error) {
        console.error('Failed to fetch studio data:', error);
        setStudioData((prev) => ({ ...prev, isLoading: false }));
      }
    };

    fetchStudioData();
  }, [sessionId]);

  const reorderClips = (startIndex: number, endIndex: number) => {
    setStudioData((prev) => {
      const newClips = Array.from(prev.clips);
      const [removed] = newClips.splice(startIndex, 1);
      newClips.splice(endIndex, 0, removed);
      return {
        ...prev,
        clips: newClips.map((clip, index) => ({ ...clip, order: index })),
      };
    });
  };

  const removeClip = (clipId: string) => {
    setStudioData((prev) => ({
      ...prev,
      clips: prev.clips.filter((c) => c.id !== clipId),
    }));
  };

  // Voice management
  const selectVoice = (styleId: VoiceStyleId) => {
    setStudioData((prev) => ({ ...prev, selectedVoice: styleId }));
  };

  const generateVoiceSample = (config: {
    style: VoiceStyleId;
    speakingRate: number;
    pitch: number;
    script: string;
  }) => {
    const sample: VoiceSample = {
      id: `voice-${Date.now()}-${Math.random().toString(36).substr(2, 6)}`,
      label: `${config.style} @ ${config.speakingRate}x`,
      style: config.style,
      speakingRate: config.speakingRate,
      pitch: config.pitch,
      script: config.script,
      status: 'generating',
    };

    setStudioData((prev) => ({
      ...prev,
      voiceSamples: [...prev.voiceSamples, sample],
      selectedVoice: config.style,
    }));

    // Simulate generation (backend call would go here)
    setTimeout(() => {
      setStudioData((prev) => ({
        ...prev,
        voiceSamples: prev.voiceSamples.map((s) =>
          s.id === sample.id ? { ...s, status: 'ready' as const } : s
        ),
      }));
    }, 2000);
  };

  // Music management
  const selectMusic = (sampleId: string) => {
    setStudioData((prev) => ({ ...prev, selectedMusic: sampleId }));
  };

  const generateMusicSample = (config: {
    prompt: string;
    durationSeconds: number;
    genre: string;
    mood: string;
    instruments: string;
  }) => {
    const sample: MusicSample = {
      id: `music-${Date.now()}-${Math.random().toString(36).substr(2, 6)}`,
      name: `${config.genre} - ${config.mood}`,
      genre: config.genre,
      mood: config.mood,
      instruments: config.instruments,
      prompt: config.prompt,
      durationSeconds: config.durationSeconds,
      status: 'generating',
    };

    setStudioData((prev) => ({
      ...prev,
      musicSamples: [...prev.musicSamples, sample],
      selectedMusic: sample.id,
    }));

    // Simulate generation (backend call would go here)
    setTimeout(() => {
      setStudioData((prev) => ({
        ...prev,
        musicSamples: prev.musicSamples.map((s) =>
          s.id === sample.id ? { ...s, status: 'ready' as const } : s
        ),
      }));
    }, 3000);
  };

  const removeMusicSample = (sampleId: string) => {
    setStudioData((prev) => ({
      ...prev,
      musicSamples: prev.musicSamples.filter((s) => s.id !== sampleId),
      selectedMusic: prev.selectedMusic === sampleId ? null : prev.selectedMusic,
    }));
  };

  return {
    ...studioData,
    reorderClips,
    removeClip,
    selectVoice,
    generateVoiceSample,
    selectMusic,
    generateMusicSample,
    removeMusicSample,
  };
}
