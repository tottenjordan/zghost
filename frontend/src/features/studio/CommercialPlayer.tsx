import { useState } from 'react';
import type { CommercialData } from './types';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';

interface CommercialPlayerProps {
  commercial: CommercialData;
}

export function CommercialPlayer({ commercial }: CommercialPlayerProps) {
  const [videoError, setVideoError] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [showOverlay, setShowOverlay] = useState(false);

  const handleDownload = () => {
    const a = document.createElement('a');
    a.href = commercial.url;
    a.download = 'commercial_30s.mp4';
    a.click();
  };

  return (
    <Card className="bg-black">
      <CardHeader>
        <CardTitle>{commercial.title}</CardTitle>
      </CardHeader>
      <CardContent>
        {/* Video Player */}
        <div className="relative mb-4 aspect-video w-full overflow-hidden rounded-lg bg-zinc-900">
          {isLoading && (
            <div className="absolute inset-0 z-10 flex items-center justify-center bg-black/50">
              <div className="h-12 w-12 animate-spin rounded-full border-4 border-zinc-700 border-t-blue-500" />
            </div>
          )}

          {!videoError ? (
            <video
              src={commercial.url}
              controls
              className="h-full w-full"
              onLoadedData={() => setIsLoading(false)}
              onError={() => {
                setVideoError(true);
                setIsLoading(false);
              }}
            >
              Your browser does not support the video tag.
            </video>
          ) : (
            <div className="flex h-full w-full items-center justify-center">
              <div className="text-center">
                <p className="text-zinc-400">Failed to load commercial</p>
                <p className="mt-2 text-xs text-zinc-500">{commercial.url}</p>
              </div>
            </div>
          )}

          {/* Scene overlay toggle */}
          {commercial.scenes && (
            <button
              onClick={() => setShowOverlay(!showOverlay)}
              className="absolute bottom-4 right-4 rounded bg-black/70 px-3 py-1.5 text-xs text-white hover:bg-black/90"
            >
              {showOverlay ? 'Hide' : 'Show'} Scenes
            </button>
          )}

          {/* Scene descriptions overlay */}
          {showOverlay && commercial.scenes && (
            <div className="absolute bottom-16 right-4 max-w-xs rounded-lg bg-black/90 p-3 backdrop-blur">
              <p className="mb-2 text-xs font-semibold text-zinc-300">Scenes</p>
              <div className="space-y-2">
                {commercial.scenes.map((scene, idx) => (
                  <div
                    key={idx}
                    className="border-l-2 border-blue-500 pl-2 text-xs text-zinc-400"
                  >
                    <span className="font-medium text-zinc-300">
                      {scene.startTime.toFixed(1)}s - {scene.endTime.toFixed(1)}s
                    </span>
                    <p className="mt-0.5">{scene.description}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Metadata */}
        <div className="mb-4 space-y-3">
          {commercial.narrativeArc && (
            <div>
              <h4 className="mb-1 text-sm font-medium text-zinc-300">
                Narrative Arc
              </h4>
              <p className="text-sm text-zinc-400">{commercial.narrativeArc}</p>
            </div>
          )}

          {commercial.targetAudience && (
            <div>
              <h4 className="mb-1 text-sm font-medium text-zinc-300">
                Target Audience Appeal
              </h4>
              <p className="text-sm text-zinc-400">{commercial.targetAudience}</p>
            </div>
          )}

          {commercial.trendConnections && (
            <div>
              <h4 className="mb-1 text-sm font-medium text-zinc-300">
                Trend Connections
              </h4>
              <p className="text-sm text-zinc-400">{commercial.trendConnections}</p>
            </div>
          )}

          <div className="flex items-center gap-4 text-sm text-zinc-500">
            <span>Duration: {commercial.duration}s</span>
            {commercial.scenes && (
              <span>Scenes: {commercial.scenes.length}</span>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-2">
          <Button
            variant="primary"
            size="md"
            className="flex-1"
            onClick={handleDownload}
          >
            Download Commercial
          </Button>
          <Button variant="secondary" size="md" disabled>
            Share
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
