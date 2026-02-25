import { useState } from 'react';

interface ContentViewerProps {
  content: {
    type: 'ad_copy' | 'visual_concept' | 'commercial' | 'report';
    data: any;
  };
  comparisonContent?: {
    type: 'ad_copy' | 'visual_concept' | 'commercial' | 'report';
    data: any;
  };
}

export function ContentViewer({ content, comparisonContent }: ContentViewerProps) {
  const [zoom, setZoom] = useState(1);
  const [showComparison, setShowComparison] = useState(false);

  const renderContent = (item: ContentViewerProps['content']) => {
    switch (item.type) {
      case 'ad_copy':
        return (
          <div className="prose prose-invert max-w-none rounded-lg border border-zinc-700 bg-zinc-900 p-6">
            <div
              className="text-zinc-50"
              dangerouslySetInnerHTML={{
                __html: item.data.html || item.data.text?.replace(/\n/g, '<br>') || 'No content',
              }}
            />
          </div>
        );

      case 'visual_concept':
        return (
          <div className="relative overflow-hidden rounded-lg border border-zinc-700 bg-zinc-900">
            {item.data.url ? (
              <div className="flex items-center justify-center p-4" style={{ transform: `scale(${zoom})` }}>
                <img
                  src={item.data.url}
                  alt="Visual concept"
                  className="max-h-[600px] w-auto rounded"
                />
              </div>
            ) : (
              <div className="flex h-96 items-center justify-center text-zinc-500">
                No image available
              </div>
            )}
            {item.data.url && (
              <div className="absolute bottom-4 right-4 flex gap-2 rounded bg-black/50 p-2">
                <button
                  onClick={() => setZoom(Math.max(0.5, zoom - 0.25))}
                  className="rounded bg-zinc-800 px-2 py-1 text-sm text-zinc-300 hover:bg-zinc-700"
                >
                  -
                </button>
                <span className="px-2 py-1 text-sm text-zinc-300">
                  {Math.round(zoom * 100)}%
                </span>
                <button
                  onClick={() => setZoom(Math.min(3, zoom + 0.25))}
                  className="rounded bg-zinc-800 px-2 py-1 text-sm text-zinc-300 hover:bg-zinc-700"
                >
                  +
                </button>
              </div>
            )}
          </div>
        );

      case 'commercial':
        return (
          <div className="rounded-lg border border-zinc-700 bg-zinc-900">
            {item.data.url ? (
              <video
                controls
                className="w-full"
                src={item.data.url}
              >
                Your browser does not support video playback.
              </video>
            ) : (
              <div className="flex h-96 items-center justify-center text-zinc-500">
                No video available
              </div>
            )}
            {item.data.scenes && (
              <div className="border-t border-zinc-700 p-4">
                <h4 className="mb-2 text-sm font-semibold text-zinc-300">Scenes</h4>
                <div className="space-y-1">
                  {item.data.scenes.map((scene: any, index: number) => (
                    <div key={index} className="text-sm text-zinc-400">
                      <span className="font-mono text-zinc-500">
                        {scene.startTime}s - {scene.endTime}s:
                      </span>{' '}
                      {scene.description}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        );

      case 'report':
        return (
          <div className="h-[600px] overflow-y-auto rounded-lg border border-zinc-700 bg-zinc-900 p-6">
            <div
              className="prose prose-invert max-w-none text-zinc-50"
              dangerouslySetInnerHTML={{
                __html: item.data.html || item.data.text?.replace(/\n/g, '<br>') || 'No content',
              }}
            />
          </div>
        );

      default:
        return (
          <div className="flex h-96 items-center justify-center text-zinc-500">
            Unsupported content type
          </div>
        );
    }
  };

  return (
    <div className="space-y-4">
      {comparisonContent && (
        <div className="flex justify-end">
          <button
            onClick={() => setShowComparison(!showComparison)}
            className="rounded bg-zinc-800 px-3 py-1 text-sm text-zinc-300 hover:bg-zinc-700"
          >
            {showComparison ? 'Single View' : 'Compare A/B'}
          </button>
        </div>
      )}

      {showComparison && comparisonContent ? (
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <h3 className="mb-2 text-sm font-semibold text-zinc-300">Version A</h3>
            {renderContent(content)}
          </div>
          <div>
            <h3 className="mb-2 text-sm font-semibold text-zinc-300">Version B</h3>
            {renderContent(comparisonContent)}
          </div>
        </div>
      ) : (
        renderContent(content)
      )}
    </div>
  );
}
