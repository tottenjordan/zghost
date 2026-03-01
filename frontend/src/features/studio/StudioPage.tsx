import { useState, useEffect } from 'react';
import { Download, ChevronDown, Film, Image, FileText, Loader2 } from 'lucide-react';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../components/ui/Tabs';
import { TimelineEditor } from './TimelineEditor';
import { ClipViewer } from './ClipViewer';
import { ClipLibrary } from './ClipLibrary';
import { CharacterGallery } from './CharacterGallery';
import { CommercialPlayer } from './CommercialPlayer';
import { AgentActivityPanel } from './AgentActivityPanel';
import { VoiceSelector } from './VoiceSelector';
import { MusicSelector } from './MusicSelector';
import { useStudio } from './useStudio';
import { Spinner } from '../../components/ui/Spinner';
import { api } from '../../services/api';
import type { SessionSummary } from '../../services/api';
import type { Clip } from './types';

export function StudioPage() {
  const [sessionId, setSessionId] = useState<string | null>(() => {
    const params = new URLSearchParams(window.location.search);
    return params.get('session') || null;
  });

  const [availableSessions, setAvailableSessions] = useState<SessionSummary[]>([]);
  const [loadingSessions, setLoadingSessions] = useState(false);
  const [pickerOpen, setPickerOpen] = useState(false);

  const [selectedClip, setSelectedClip] = useState<Clip | null>(null);
  const [voiceDirections, setVoiceDirections] = useState<string[]>([]);

  const {
    clips,
    characters,
    commercial,
    voiceSamples,
    musicSamples,
    selectedVoice,
    selectedMusic,
    isLoading,
    reorderClips,
    removeClip,
    selectVoice,
    generateVoiceSample,
    selectMusic,
    generateMusicSample,
    removeMusicSample,
  } = useStudio(sessionId);

  const handleSelectClip = (clip: Clip) => {
    setSelectedClip(clip);
  };

  const handleRemoveClip = (clipId: string) => {
    removeClip(clipId);
    if (selectedClip?.id === clipId) {
      setSelectedClip(null);
    }
  };

  // Fetch available sessions with AV assets on mount
  useEffect(() => {
    const fetchSessions = async () => {
      setLoadingSessions(true);
      try {
        const result = await api.listSessions();
        // Show sessions that have videos or commercials
        const withAssets = result.sessions.filter(
          (s) => s.has_commercial || s.has_videos || (s.video_count && s.video_count > 0)
        );
        setAvailableSessions(withAssets);
        // If no session selected and we have sessions, auto-select the most recent
        if (!sessionId && withAssets.length > 0) {
          const latest = withAssets.sort(
            (a, b) => (b.last_update_time || 0) - (a.last_update_time || 0)
          )[0];
          setSessionId(latest.session_id);
        }
      } catch (err) {
        console.error('Failed to fetch sessions:', err);
      } finally {
        setLoadingSessions(false);
      }
    };
    fetchSessions();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSelectSession = (sid: string) => {
    setSessionId(sid);
    setPickerOpen(false);
    setSelectedClip(null);
    // Update URL without full reload
    const url = new URL(window.location.href);
    url.searchParams.set('session', sid);
    window.history.replaceState({}, '', url.toString());
  };

  const selectedSessionInfo = availableSessions.find((s) => s.session_id === sessionId);

  // Voice action listener for studio direction
  useEffect(() => {
    const handler = (e: Event) => {
      const { action, params } = (e as CustomEvent).detail;
      if (action === 'send_studio_direction' && params?.direction) {
        setVoiceDirections(prev => [...prev, params.direction]);
      }
    };
    window.addEventListener('voice-action', handler);
    return () => window.removeEventListener('voice-action', handler);
  }, []);

  return (
    <div className="space-y-6">
      {/* Header with Run Picker */}
      <div>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="mb-1 text-2xl font-bold text-zinc-50">AV Studio</h1>
            <p className="text-sm text-zinc-400">
              Video editing workspace for your commercial
            </p>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            {sessionId && (
              <button
                onClick={async () => {
                  try {
                    await api.exportSession(sessionId);
                  } catch (err) {
                    console.error('Export failed:', err);
                  }
                }}
                className="inline-flex items-center gap-2 px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
              >
                <Download className="w-4 h-4" />
                Export
              </button>
            )}
          </div>
        </div>

        {/* Run Picker */}
        <div className="mt-3 relative">
          <button
            onClick={() => setPickerOpen(!pickerOpen)}
            className="w-full flex items-center justify-between gap-3 px-4 py-3 rounded-lg border border-zinc-700 bg-zinc-900/50 hover:bg-zinc-800/50 transition-colors text-left"
          >
            {loadingSessions ? (
              <div className="flex items-center gap-2 text-sm text-zinc-400">
                <Loader2 className="w-4 h-4 animate-spin" />
                Loading runs...
              </div>
            ) : sessionId ? (
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-zinc-200 truncate">
                    {selectedSessionInfo?.brand || 'Run'}{' '}
                    {selectedSessionInfo?.target_product ? `/ ${selectedSessionInfo.target_product}` : ''}
                  </span>
                  {selectedSessionInfo?.has_commercial && (
                    <span className="flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] rounded bg-amber-950/20 text-amber-400 border border-amber-800/20">
                      <Film className="w-2.5 h-2.5" /> Commercial
                    </span>
                  )}
                  {(selectedSessionInfo?.video_count ?? 0) > 0 && (
                    <span className="flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] rounded bg-green-950/20 text-green-400 border border-green-800/20">
                      <Film className="w-2.5 h-2.5" /> {selectedSessionInfo?.video_count} clips
                    </span>
                  )}
                  {(selectedSessionInfo?.image_count ?? 0) > 0 && (
                    <span className="flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] rounded bg-cyan-950/20 text-cyan-400 border border-cyan-800/20">
                      <Image className="w-2.5 h-2.5" /> {selectedSessionInfo?.image_count} images
                    </span>
                  )}
                </div>
                <span className="text-[11px] text-zinc-500 font-mono">{sessionId.slice(0, 16)}...</span>
              </div>
            ) : (
              <span className="text-sm text-zinc-500">Select a pipeline run...</span>
            )}
            <ChevronDown className={`w-4 h-4 text-zinc-400 transition-transform ${pickerOpen ? 'rotate-180' : ''}`} />
          </button>

          {/* Dropdown */}
          {pickerOpen && (
            <div className="absolute z-50 w-full mt-1 max-h-64 overflow-y-auto rounded-lg border border-zinc-700 bg-zinc-900 shadow-xl">
              {availableSessions.length === 0 ? (
                <div className="px-4 py-6 text-center text-sm text-zinc-500">
                  No runs with AV assets found
                </div>
              ) : (
                availableSessions
                  .sort((a, b) => (b.last_update_time || 0) - (a.last_update_time || 0))
                  .map((s) => (
                    <button
                      key={s.session_id}
                      onClick={() => handleSelectSession(s.session_id)}
                      className={`w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-zinc-800 transition-colors border-b border-zinc-800 last:border-0 ${
                        s.session_id === sessionId ? 'bg-zinc-800/60' : ''
                      }`}
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-zinc-200">
                            {s.brand || 'Run'} {s.target_product ? `/ ${s.target_product}` : ''}
                          </span>
                          {s.commercial_duration && (
                            <span className="text-[10px] text-zinc-500">{s.commercial_duration}s</span>
                          )}
                        </div>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="text-[10px] text-zinc-500 font-mono">{s.session_id.slice(0, 12)}...</span>
                          {s.last_update_time && (
                            <span className="text-[10px] text-zinc-600">
                              {new Date(s.last_update_time * 1000).toLocaleDateString('en-US', {
                                month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
                              })}
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-1.5 flex-shrink-0">
                        {s.has_report && <FileText className="w-3.5 h-3.5 text-blue-400" />}
                        {(s.image_count ?? 0) > 0 && <Image className="w-3.5 h-3.5 text-cyan-400" />}
                        {(s.video_count ?? 0) > 0 && <Film className="w-3.5 h-3.5 text-green-400" />}
                        {s.has_commercial && <Film className="w-3.5 h-3.5 text-amber-400" />}
                      </div>
                    </button>
                  ))
              )}
            </div>
          )}
        </div>
      </div>

      {isLoading ? (
        <div className="flex h-64 items-center justify-center">
          <div className="text-center">
            <Spinner size="lg" className="mb-4 text-blue-500" />
            <p className="text-zinc-400">Loading studio data...</p>
          </div>
        </div>
      ) : (
        <>
          {/* Commercial Player (if available) */}
          {commercial && (
            <div className="mb-6">
              <CommercialPlayer commercial={commercial} />
            </div>
          )}

          {/* Voice Directions */}
          {voiceDirections.length > 0 && (
            <div className="rounded-lg border border-blue-800 bg-blue-950/30 px-4 py-3">
              <p className="text-xs font-medium text-blue-400 mb-2">Voice Directions</p>
              {voiceDirections.map((d, i) => (
                <p key={i} className="text-sm text-zinc-300">&bull; {d}</p>
              ))}
            </div>
          )}

          {/* Timeline Editor */}
          <TimelineEditor
            clips={clips}
            onReorder={reorderClips}
            onSelectClip={handleSelectClip}
            selectedClipId={selectedClip?.id}
          />

          {/* Main Content Tabs */}
          <Tabs defaultValue="clips">
            <TabsList>
              <TabsTrigger value="clips">Clips ({clips.length})</TabsTrigger>
              <TabsTrigger value="voice">Voice</TabsTrigger>
              <TabsTrigger value="music">Music</TabsTrigger>
              <TabsTrigger value="timeline">Timeline</TabsTrigger>
              <TabsTrigger value="characters">
                Characters ({characters.length})
              </TabsTrigger>
              <TabsTrigger value="activity">Agent Activity</TabsTrigger>
            </TabsList>

            <TabsContent value="clips">
              <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
                {/* Clip Library */}
                <div className="lg:col-span-2">
                  <ClipLibrary
                    clips={clips}
                    onSelectClip={handleSelectClip}
                    selectedClipId={selectedClip?.id}
                  />
                </div>

                {/* Selected Clip Viewer */}
                <div>
                  {selectedClip ? (
                    <ClipViewer clip={selectedClip} onRemove={handleRemoveClip} />
                  ) : (
                    <div className="flex h-full min-h-[300px] items-center justify-center rounded-lg border border-dashed border-zinc-700 bg-zinc-900/50">
                      <p className="text-zinc-500">
                        Select a clip to view details
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </TabsContent>

            <TabsContent value="voice">
              <VoiceSelector
                samples={voiceSamples}
                selectedVoice={selectedVoice}
                onSelectVoice={selectVoice}
                onGenerateSample={generateVoiceSample}
              />
            </TabsContent>

            <TabsContent value="music">
              <MusicSelector
                samples={musicSamples}
                selectedMusicId={selectedMusic}
                onSelectMusic={selectMusic}
                onGenerateSample={generateMusicSample}
                onRemoveSample={removeMusicSample}
              />
            </TabsContent>

            <TabsContent value="timeline">
              <div className="space-y-4">
                <p className="text-sm text-zinc-400">
                  Drag clips to reorder them in your commercial timeline
                </p>
                {selectedClip && (
                  <ClipViewer clip={selectedClip} onRemove={handleRemoveClip} />
                )}
              </div>
            </TabsContent>

            <TabsContent value="characters">
              <CharacterGallery characters={characters} />
            </TabsContent>

            <TabsContent value="activity">
              <AgentActivityPanel sessionId={sessionId} />
            </TabsContent>
          </Tabs>
        </>
      )}
    </div>
  );
}
