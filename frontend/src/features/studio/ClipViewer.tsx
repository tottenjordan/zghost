import { useState } from 'react';
import type { Clip } from './types';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';

interface ClipViewerProps {
  clip: Clip;
  onRemove: (clipId: string) => void;
}

export function ClipViewer({ clip, onRemove }: ClipViewerProps) {
  const [videoError, setVideoError] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const getStatusVariant = (status: Clip['status']) => {
    switch (status) {
      case 'ready':
        return 'success';
      case 'generating':
        return 'warning';
      case 'error':
        return 'error';
      default:
        return 'default';
    }
  };

  return (
    <Card className="bg-black">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>{clip.name}</CardTitle>
          <Badge variant={getStatusVariant(clip.status)}>
            {clip.status}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        {/* Video Player */}
        <div className="mb-4">
          {clip.status === 'ready' && !videoError ? (
            <div className="relative aspect-video w-full overflow-hidden rounded-lg bg-zinc-900">
              {isLoading && (
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="h-8 w-8 animate-spin rounded-full border-4 border-zinc-700 border-t-blue-500" />
                </div>
              )}
              <video
                src={clip.url}
                controls
                className="h-full w-full"
                poster={clip.firstFrameUrl}
                onLoadedData={() => setIsLoading(false)}
                onError={() => {
                  setVideoError(true);
                  setIsLoading(false);
                }}
              >
                Your browser does not support the video tag.
              </video>
            </div>
          ) : clip.status === 'generating' ? (
            <div className="flex aspect-video w-full items-center justify-center rounded-lg bg-zinc-900">
              <div className="text-center">
                <div className="mb-2 h-8 w-8 animate-spin rounded-full border-4 border-zinc-700 border-t-yellow-500" />
                <p className="text-sm text-zinc-400">Generating clip...</p>
              </div>
            </div>
          ) : (
            <div className="flex aspect-video w-full items-center justify-center rounded-lg border-2 border-dashed border-zinc-700 bg-zinc-900">
              <div className="text-center">
                <p className="mb-2 text-sm text-zinc-400">
                  {clip.status === 'error' || videoError
                    ? 'Failed to load video'
                    : clip.sceneDescription}
                </p>
                {(clip.status === 'error' || videoError) && (
                  <p className="mt-1 text-[10px] text-zinc-600 truncate max-w-full" title={clip.url}>
                    {clip.url}
                  </p>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Clip Metadata */}
        <div className="mb-4 space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-zinc-400">Duration</span>
            <span className="text-zinc-100">{clip.duration}s</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-zinc-400">Scene</span>
            <span className="text-zinc-100">{clip.sceneDescription}</span>
          </div>
          {clip.generationParams?.prompt && (
            <div className="text-sm">
              <span className="text-zinc-400">Prompt</span>
              <p className="mt-1 rounded bg-zinc-900 p-2 text-xs text-zinc-300">
                {clip.generationParams.prompt}
              </p>
            </div>
          )}
        </div>

        {/* Frame Previews */}
        {(clip.firstFrameUrl || clip.lastFrameUrl) && (
          <div className="mb-4">
            <p className="mb-2 text-sm text-zinc-400">Frames</p>
            <div className="flex gap-2">
              {clip.firstFrameUrl && (
                <div className="flex-1">
                  <img
                    src={clip.firstFrameUrl}
                    alt="First frame"
                    className="aspect-video w-full rounded border border-zinc-700 object-cover"
                  />
                  <p className="mt-1 text-xs text-zinc-500">First frame</p>
                </div>
              )}
              {clip.lastFrameUrl && (
                <div className="flex-1">
                  <img
                    src={clip.lastFrameUrl}
                    alt="Last frame"
                    className="aspect-video w-full rounded border border-zinc-700 object-cover"
                  />
                  <p className="mt-1 text-xs text-zinc-500">Last frame</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-2">
          <Button variant="secondary" size="sm" className="flex-1" disabled>
            Re-generate
          </Button>
          <Button
            variant="danger"
            size="sm"
            onClick={() => onRemove(clip.id)}
            disabled={clip.status === 'generating'}
          >
            Remove
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
