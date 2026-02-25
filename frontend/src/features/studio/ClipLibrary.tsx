import { useState } from 'react';
import type { Clip } from './types';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';

interface ClipLibraryProps {
  clips: Clip[];
  onSelectClip: (clip: Clip) => void;
  selectedClipId?: string;
}

export function ClipLibrary({
  clips,
  onSelectClip,
  selectedClipId,
}: ClipLibraryProps) {
  const [filter, setFilter] = useState<'all' | 'ready' | 'generating' | 'error'>(
    'all'
  );

  const filteredClips = clips.filter((clip) => {
    if (filter === 'all') return true;
    return clip.status === filter;
  });

  const sortedClips = [...filteredClips].sort((a, b) => a.order - b.order);

  return (
    <div>
      {/* Filter Controls */}
      <div className="mb-4 flex items-center gap-2">
        <span className="text-sm text-zinc-400">Filter:</span>
        <button
          onClick={() => setFilter('all')}
          className={`rounded px-3 py-1 text-sm transition-colors ${
            filter === 'all'
              ? 'bg-blue-600 text-white'
              : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
          }`}
        >
          All ({clips.length})
        </button>
        <button
          onClick={() => setFilter('ready')}
          className={`rounded px-3 py-1 text-sm transition-colors ${
            filter === 'ready'
              ? 'bg-blue-600 text-white'
              : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
          }`}
        >
          Ready ({clips.filter((c) => c.status === 'ready').length})
        </button>
        <button
          onClick={() => setFilter('generating')}
          className={`rounded px-3 py-1 text-sm transition-colors ${
            filter === 'generating'
              ? 'bg-blue-600 text-white'
              : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
          }`}
        >
          Generating ({clips.filter((c) => c.status === 'generating').length})
        </button>
        <button
          onClick={() => setFilter('error')}
          className={`rounded px-3 py-1 text-sm transition-colors ${
            filter === 'error'
              ? 'bg-blue-600 text-white'
              : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
          }`}
        >
          Error ({clips.filter((c) => c.status === 'error').length})
        </button>
      </div>

      {/* Clip Grid */}
      {sortedClips.length === 0 ? (
        <div className="flex h-48 items-center justify-center rounded-lg border border-dashed border-zinc-700 bg-zinc-900/50">
          <p className="text-zinc-500">
            {filter === 'all'
              ? 'No clips generated yet'
              : `No ${filter} clips`}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-4">
          {sortedClips.map((clip) => {
            const isSelected = clip.id === selectedClipId;

            return (
              <Card
                key={clip.id}
                onClick={() => onSelectClip(clip)}
                className={`cursor-pointer transition-all hover:border-zinc-600 ${
                  isSelected ? 'border-blue-500 ring-2 ring-blue-500/50' : ''
                }`}
              >
                {/* Thumbnail */}
                <div className="relative aspect-video w-full overflow-hidden rounded-t-lg bg-zinc-900">
                  {clip.thumbnailUrl ? (
                    <img
                      src={clip.thumbnailUrl}
                      alt={clip.name}
                      className="h-full w-full object-cover"
                    />
                  ) : (
                    <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-zinc-800 to-zinc-900">
                      {clip.status === 'generating' ? (
                        <div className="h-6 w-6 animate-spin rounded-full border-2 border-zinc-700 border-t-yellow-500" />
                      ) : (
                        <svg
                          className="h-8 w-8 text-zinc-600"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
                          />
                        </svg>
                      )}
                    </div>
                  )}

                  {/* Order badge */}
                  <div className="absolute left-2 top-2 rounded-full bg-black/70 px-2 py-0.5 text-xs font-medium text-white">
                    #{clip.order + 1}
                  </div>

                  {/* Status badge */}
                  <div className="absolute right-2 top-2">
                    <Badge
                      variant={
                        clip.status === 'ready'
                          ? 'success'
                          : clip.status === 'generating'
                            ? 'warning'
                            : 'error'
                      }
                    >
                      {clip.status}
                    </Badge>
                  </div>
                </div>

                {/* Clip info */}
                <div className="p-3">
                  <h4 className="mb-1 truncate text-sm font-medium text-zinc-100">
                    {clip.name}
                  </h4>
                  <p className="mb-2 truncate text-xs text-zinc-400">
                    {clip.sceneDescription}
                  </p>
                  <div className="flex items-center justify-between text-xs text-zinc-500">
                    <span>{clip.duration}s</span>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
