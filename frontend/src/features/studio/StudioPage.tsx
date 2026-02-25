import { useState } from 'react';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../components/ui/Tabs';
import { TimelineEditor } from './TimelineEditor';
import { ClipViewer } from './ClipViewer';
import { ClipLibrary } from './ClipLibrary';
import { CharacterGallery } from './CharacterGallery';
import { CommercialPlayer } from './CommercialPlayer';
import { AgentActivityPanel } from './AgentActivityPanel';
import { useStudio } from './useStudio';
import { Spinner } from '../../components/ui/Spinner';
import type { Clip } from './types';

export function StudioPage() {
  const [sessionId] = useState<string | null>(() => {
    const params = new URLSearchParams(window.location.search);
    return params.get('session') || null;
  });

  const [selectedClip, setSelectedClip] = useState<Clip | null>(null);

  const { clips, characters, commercial, isLoading, reorderClips, removeClip } =
    useStudio(sessionId);

  const handleSelectClip = (clip: Clip) => {
    setSelectedClip(clip);
  };

  const handleRemoveClip = (clipId: string) => {
    removeClip(clipId);
    if (selectedClip?.id === clipId) {
      setSelectedClip(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="mb-2 text-3xl font-bold text-zinc-50">AV Studio</h1>
        <p className="text-zinc-400">
          Video editing workspace for your 30-second commercial
        </p>
        {sessionId && (
          <p className="mt-1 text-xs text-zinc-600">Session: {sessionId}</p>
        )}
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
