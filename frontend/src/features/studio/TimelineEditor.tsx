import { useState } from 'react';
import type { Clip, AudioTrack, MusicSample } from './types';
import { Badge } from '../../components/ui/Badge';
import { Music, Play, Trash2 } from 'lucide-react';

interface TimelineEditorProps {
  clips: Clip[];
  onReorder: (startIndex: number, endIndex: number) => void;
  onSelectClip: (clip: Clip) => void;
  selectedClipId?: string;
  audioTracks?: AudioTrack[];
  musicSamples?: MusicSample[];
  onAddAudioTrack?: (musicSampleId: string) => void;
  onRemoveAudioTrack?: (trackId: string) => void;
}

export function TimelineEditor({
  clips,
  onReorder,
  onSelectClip,
  selectedClipId,
  audioTracks = [],
  musicSamples = [],
  onAddAudioTrack,
  onRemoveAudioTrack,
}: TimelineEditorProps) {
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);
  const [audioDragOver, setAudioDragOver] = useState(false);

  const totalDuration = clips.reduce((sum, clip) => sum + clip.duration, 0);
  const targetDuration = 30;

  const handleDragStart = (index: number) => {
    setDraggedIndex(index);
  };

  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault();
    if (draggedIndex === null || draggedIndex === index) return;

    onReorder(draggedIndex, index);
    setDraggedIndex(index);
  };

  const handleDragEnd = () => {
    setDraggedIndex(null);
  };

  // Audio track drop handlers
  const handleAudioDragOver = (e: React.DragEvent) => {
    if (e.dataTransfer.types.includes('application/x-music-sample')) {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'copy';
      setAudioDragOver(true);
    }
  };

  const handleAudioDragLeave = () => {
    setAudioDragOver(false);
  };

  const handleAudioDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setAudioDragOver(false);
    const musicSampleId = e.dataTransfer.getData('application/x-music-sample');
    if (musicSampleId && onAddAudioTrack) {
      onAddAudioTrack(musicSampleId);
    }
  };

  return (
    <div className="rounded-lg border border-zinc-800 bg-black p-4">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-zinc-100">Timeline</h3>
        <div className="flex items-center gap-4">
          <span className="text-sm text-zinc-400">
            Duration: {totalDuration}s / {targetDuration}s
          </span>
          {totalDuration !== targetDuration && (
            <Badge variant={totalDuration > targetDuration ? 'warning' : 'info'}>
              {totalDuration > targetDuration ? 'Needs trim' : 'Under target'}
            </Badge>
          )}
        </div>
      </div>

      <div className="relative space-y-1">
        {/* Video clip track */}
        <div className="flex items-center gap-2">
          <span className="w-14 shrink-0 text-right text-[10px] font-medium uppercase tracking-wide text-zinc-500">
            Video
          </span>
          <div className="flex flex-1 gap-1 overflow-x-auto rounded bg-zinc-900 p-2">
            {clips.length === 0 ? (
              <div className="flex h-24 w-full items-center justify-center text-zinc-500">
                No clips yet. Generate clips to build your commercial.
              </div>
            ) : (
              clips.map((clip, index) => {
                const widthPercent = (clip.duration / totalDuration) * 100;
                const isSelected = clip.id === selectedClipId;

                return (
                  <div
                    key={clip.id}
                    draggable
                    onDragStart={() => handleDragStart(index)}
                    onDragOver={(e) => handleDragOver(e, index)}
                    onDragEnd={handleDragEnd}
                    onClick={() => onSelectClip(clip)}
                    style={{ width: `${widthPercent}%` }}
                    className={`group relative flex h-24 min-w-[80px] cursor-pointer flex-col items-center justify-center rounded border-2 transition-all ${
                      isSelected
                        ? 'border-blue-500 bg-blue-900/30'
                        : 'border-zinc-700 bg-zinc-800 hover:border-zinc-600'
                    } ${draggedIndex === index ? 'opacity-50' : ''}`}
                  >
                    {clip.thumbnailUrl ? (
                      <img
                        src={clip.thumbnailUrl}
                        alt={clip.name}
                        className="absolute inset-0 h-full w-full rounded object-cover opacity-40"
                      />
                    ) : (
                      <div className="absolute inset-0 rounded bg-gradient-to-br from-zinc-700 to-zinc-800 opacity-40" />
                    )}

                    <div className="relative z-10 flex flex-col items-center gap-1 px-2 text-center">
                      <span className="text-xs font-medium text-zinc-100">
                        {clip.name}
                      </span>
                      <span className="text-xs text-zinc-400">{clip.duration}s</span>
                    </div>

                    <div className="absolute right-1 top-1">
                      {clip.status === 'generating' && (
                        <div className="h-2 w-2 animate-pulse rounded-full bg-yellow-500" />
                      )}
                      {clip.status === 'error' && (
                        <div className="h-2 w-2 rounded-full bg-red-500" />
                      )}
                      {clip.status === 'ready' && (
                        <div className="h-2 w-2 rounded-full bg-green-500" />
                      )}
                    </div>

                    <div className="absolute bottom-1 left-1 rounded bg-black/60 px-1 text-xs text-zinc-300">
                      #{index + 1}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Audio track lane */}
        <div className="flex items-center gap-2">
          <span className="w-14 shrink-0 text-right text-[10px] font-medium uppercase tracking-wide text-purple-400">
            Audio
          </span>
          <div
            onDragOver={handleAudioDragOver}
            onDragLeave={handleAudioDragLeave}
            onDrop={handleAudioDrop}
            className={`flex flex-1 gap-1 overflow-x-auto rounded p-2 transition-colors ${
              audioDragOver
                ? 'border-2 border-dashed border-purple-500 bg-purple-950/30'
                : 'border-2 border-transparent bg-zinc-900/60'
            }`}
          >
            {audioTracks.length === 0 ? (
              <div className="flex h-12 w-full items-center justify-center gap-2 text-zinc-600">
                <Music className="h-4 w-4" />
                <span className="text-xs">
                  {audioDragOver
                    ? 'Drop music here'
                    : 'Drag a music track here from the Music tab'}
                </span>
              </div>
            ) : (
              audioTracks.map((track) => (
                <div
                  key={track.id}
                  className="group relative flex h-12 min-w-[120px] flex-1 items-center gap-2 rounded border border-purple-800 bg-purple-950/40 px-3"
                >
                  <Music className="h-3.5 w-3.5 shrink-0 text-purple-400" />
                  <div className="flex-1 min-w-0">
                    <span className="block truncate text-xs font-medium text-purple-200">
                      {track.name}
                    </span>
                    <span className="text-[10px] text-purple-400/60">
                      {track.duration}s
                    </span>
                  </div>
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    {track.url && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          const audio = new Audio(track.url);
                          audio.play();
                        }}
                        className="rounded p-1 text-purple-300 hover:bg-purple-800/50"
                      >
                        <Play className="h-3 w-3" />
                      </button>
                    )}
                    {onRemoveAudioTrack && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onRemoveAudioTrack(track.id);
                        }}
                        className="rounded p-1 text-zinc-500 hover:bg-zinc-700 hover:text-zinc-300"
                      >
                        <Trash2 className="h-3 w-3" />
                      </button>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Target duration marker */}
        {clips.length > 0 && (
          <div className="mt-2 flex items-center gap-2">
            <div className="w-14 shrink-0" />
            <div className="flex flex-1 items-center gap-2">
              <div className="h-px flex-1 bg-zinc-700" />
              <span className="text-xs text-zinc-500">30s target</span>
              <div className="h-px flex-1 bg-zinc-700" />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
