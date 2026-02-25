import { useState } from 'react';
import { Image, Film, FileText, ExternalLink, Download, ChevronRight } from 'lucide-react';
import { Badge } from '../../components/ui/Badge';
import { cn } from '../../lib/utils';

interface ResultsGalleryProps {
  sessionState: Record<string, any>;
}

interface AdCopy {
  headline?: string;
  body?: string;
  cta?: string;
  score?: number;
}

function gcsToHttpUrl(gcsPath: string): string {
  // Convert gs://bucket/path to https://storage.googleapis.com/bucket/path
  return gcsPath.replace('gs://', 'https://storage.googleapis.com/');
}

function parseAdCopies(state: Record<string, any>): AdCopy[] {
  const raw = state.final_select_ad_copies;
  if (!raw) return [];

  // Could be a nested object with final_select_ad_copies key
  const copies = raw.final_select_ad_copies || raw;
  if (Array.isArray(copies)) {
    return copies.map((c: any) => ({
      headline: c.headline || c.title || c.name,
      body: c.body || c.description || c.text,
      cta: c.cta || c.call_to_action,
      score: c.score || c.total_score,
    }));
  }

  return [];
}

function parseMediaKeys(state: Record<string, any>): { images: string[]; videos: string[] } {
  const gcsFolder = state.gcs_folder || '';

  // Try artifact keys first
  let imgKeys = state.img_artifact_keys?.img_artifact_keys || state.img_artifact_keys || [];
  let vidKeys = state.vid_artifact_keys?.vid_artifact_keys || state.vid_artifact_keys || [];

  if (!Array.isArray(imgKeys)) imgKeys = [];
  if (!Array.isArray(vidKeys)) vidKeys = [];

  // If keys are relative paths, prepend GCS folder
  const images = imgKeys.map((k: string) =>
    k.startsWith('gs://') ? k : `gs://zghost-media-center/${gcsFolder}/${k}`
  );
  const videos = vidKeys.map((k: string) =>
    k.startsWith('gs://') ? k : `gs://zghost-media-center/${gcsFolder}/${k}`
  );

  return { images, videos };
}

export function ResultsGallery({ sessionState }: ResultsGalleryProps) {
  const [expandedCopy, setExpandedCopy] = useState<number | null>(null);
  const adCopies = parseAdCopies(sessionState);
  const { images, videos } = parseMediaKeys(sessionState);
  const gcsFolder = sessionState.gcs_folder || '';
  const hasReport = !!sessionState.combined_final_cited_report;
  const hasVisualConcepts = !!sessionState.final_visual_concepts;

  const totalMedia = images.length + videos.length;
  const hasAny = adCopies.length > 0 || totalMedia > 0 || hasReport || hasVisualConcepts;

  if (!hasAny) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8 text-center">
        <Image className="w-10 h-10 text-zinc-600 mb-3" />
        <p className="text-sm text-zinc-500">No results yet</p>
        <p className="text-xs text-zinc-600 mt-1">
          Run the pipeline to generate ad creatives
        </p>
      </div>
    );
  }

  return (
    <div className="p-3 space-y-4 overflow-y-auto h-full">
      {/* Pipeline Progress Summary */}
      <div className="flex flex-wrap gap-1.5">
        <Badge variant={hasReport ? 'success' : 'default'} className="text-xs">
          Research {hasReport ? 'Done' : 'Pending'}
        </Badge>
        <Badge variant={adCopies.length > 0 ? 'success' : 'default'} className="text-xs">
          {adCopies.length} Ad Copies
        </Badge>
        <Badge variant={hasVisualConcepts ? 'success' : 'default'} className="text-xs">
          Visuals {hasVisualConcepts ? 'Done' : 'Pending'}
        </Badge>
        <Badge variant={totalMedia > 0 ? 'success' : 'default'} className="text-xs">
          {totalMedia} Media Files
        </Badge>
      </div>

      {/* Research Report */}
      {hasReport && gcsFolder && (
        <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-3">
          <div className="flex items-center gap-2 mb-2">
            <FileText className="w-4 h-4 text-blue-400" />
            <span className="text-sm font-medium text-zinc-300">Research Report</span>
          </div>
          <a
            href={gcsToHttpUrl(`gs://zghost-media-center/${gcsFolder}/draft_research_report_with_citations.pdf`)}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 text-xs text-blue-400 hover:text-blue-300"
          >
            <ExternalLink className="w-3 h-3" />
            View PDF Report
          </a>
        </div>
      )}

      {/* Ad Copies */}
      {adCopies.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-zinc-400">Ad Copies</h3>
          {adCopies.map((copy, i) => (
            <button
              key={i}
              onClick={() => setExpandedCopy(expandedCopy === i ? null : i)}
              className="w-full text-left rounded-lg border border-zinc-800 bg-zinc-900/50 p-3 hover:border-zinc-700 transition-colors"
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-zinc-200">
                  {copy.headline || `Ad Copy ${i + 1}`}
                </span>
                <div className="flex items-center gap-2">
                  {copy.score && (
                    <Badge variant="info" className="text-xs">
                      {copy.score}/100
                    </Badge>
                  )}
                  <ChevronRight className={cn(
                    'w-3 h-3 text-zinc-500 transition-transform',
                    expandedCopy === i && 'rotate-90'
                  )} />
                </div>
              </div>
              {expandedCopy === i && (
                <div className="mt-2 space-y-1 border-t border-zinc-800 pt-2">
                  {copy.body && (
                    <p className="text-xs text-zinc-400">{copy.body}</p>
                  )}
                  {copy.cta && (
                    <p className="text-xs text-blue-400">CTA: {copy.cta}</p>
                  )}
                </div>
              )}
            </button>
          ))}
        </div>
      )}

      {/* Visual Concepts */}
      {hasVisualConcepts && (
        <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-3">
          <div className="flex items-center gap-2 mb-2">
            <Image className="w-4 h-4 text-purple-400" />
            <span className="text-sm font-medium text-zinc-300">Visual Concepts</span>
          </div>
          <p className="text-xs text-zinc-400 line-clamp-3">
            {typeof sessionState.final_visual_concepts === 'string'
              ? sessionState.final_visual_concepts.slice(0, 200) + '...'
              : 'Visual concepts generated'}
          </p>
        </div>
      )}

      {/* Generated Media */}
      {(images.length > 0 || videos.length > 0) && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-zinc-400">Generated Media</h3>

          {videos.map((url, i) => (
            <div key={`vid-${i}`} className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-3">
              <div className="flex items-center gap-2 mb-2">
                <Film className="w-4 h-4 text-green-400" />
                <span className="text-xs text-zinc-300 truncate flex-1">
                  {url.split('/').pop()}
                </span>
                <a
                  href={gcsToHttpUrl(url)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-zinc-500 hover:text-zinc-300"
                >
                  <Download className="w-3.5 h-3.5" />
                </a>
              </div>
              <video
                src={gcsToHttpUrl(url)}
                controls
                className="w-full rounded border border-zinc-700"
                preload="metadata"
              />
            </div>
          ))}

          {images.map((url, i) => (
            <div key={`img-${i}`} className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-3">
              <div className="flex items-center gap-2 mb-2">
                <Image className="w-4 h-4 text-blue-400" />
                <span className="text-xs text-zinc-300 truncate flex-1">
                  {url.split('/').pop()}
                </span>
                <a
                  href={gcsToHttpUrl(url)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-zinc-500 hover:text-zinc-300"
                >
                  <Download className="w-3.5 h-3.5" />
                </a>
              </div>
              <img
                src={gcsToHttpUrl(url)}
                alt={`Generated ad ${i + 1}`}
                className="w-full rounded border border-zinc-700"
                loading="lazy"
              />
            </div>
          ))}
        </div>
      )}

      {/* GCS Folder link */}
      {gcsFolder && (
        <div className="text-xs text-zinc-600 pt-2 border-t border-zinc-800">
          GCS: gs://zghost-media-center/{gcsFolder}/
        </div>
      )}
    </div>
  );
}
