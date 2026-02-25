import { useState } from 'react';
import type { Clip } from './types';
import { Badge } from '../../components/ui/Badge';

interface TimelineEditorProps {
  clips: Clip[];
  onReorder: (startIndex: number, endIndex: number) => void;
  onSelectClip: (clip: Clip) => void;
  selectedClipId?: string;
}

export function TimelineEditor({
  clips,
  onReorder,
  onSelectClip,
  selectedClipId,
}: TimelineEditorProps) {
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);

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

      <div className="relative">
        {/* Timeline track */}
        <div className="flex gap-1 overflow-x-auto rounded bg-zinc-900 p-2">
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
                  {/* Clip thumbnail or placeholder */}
                  {clip.thumbnailUrl ? (
                    <img
                      src={clip.thumbnailUrl}
                      alt={clip.name}
                      className="absolute inset-0 h-full w-full rounded object-cover opacity-40"
                    />
                  ) : (
                    <div className="absolute inset-0 rounded bg-gradient-to-br from-zinc-700 to-zinc-800 opacity-40" />
                  )}

                  {/* Clip info */}
                  <div className="relative z-10 flex flex-col items-center gap-1 px-2 text-center">
                    <span className="text-xs font-medium text-zinc-100">
                      {clip.name}
                    </span>
                    <span className="text-xs text-zinc-400">{clip.duration}s</span>
                  </div>

                  {/* Status indicator */}
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

                  {/* Scene number */}
                  <div className="absolute bottom-1 left-1 rounded bg-black/60 px-1 text-xs text-zinc-300">
                    #{index + 1}
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Target duration marker */}
        {clips.length > 0 && (
          <div className="mt-2 flex items-center gap-2">
            <div className="h-px flex-1 bg-zinc-700" />
            <span className="text-xs text-zinc-500">30s target</span>
            <div className="h-px flex-1 bg-zinc-700" />
          </div>
        )}
      </div>
    </div>
  );
}
