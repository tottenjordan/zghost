import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Image, Film, FileText, ExternalLink, Download, ChevronRight, ImageOff, FileWarning } from 'lucide-react';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { cn } from '../../lib/utils';

interface ResultsGalleryProps {
  sessionState: Record<string, any>;
  sessionId: string;
}

interface AdCopy {
  headline?: string;
  body?: string;
  cta?: string;
  score?: number;
}

interface MediaItem {
  url: string;
  headline?: string;
  concept?: string;
  caption?: string;
  prompt?: string;
  trend?: string;
  type: 'image' | 'video';
}

function gcsToHttpUrl(gcsPath: string): string {
  return gcsPath.replace('gs://', 'https://storage.googleapis.com/');
}

function parseAdCopies(state: Record<string, any>): AdCopy[] {
  const raw = state.final_select_ad_copies;
  if (!raw) return [];

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

function parseMediaItems(state: Record<string, any>): MediaItem[] {
  const gcsFolder = state.gcs_folder || '';
  const mediaItems: MediaItem[] = [];

  let imgKeys = state.img_artifact_keys?.img_artifact_keys || state.img_artifact_keys || [];
  let vidKeys = state.vid_artifact_keys?.vid_artifact_keys || state.vid_artifact_keys || [];

  if (!Array.isArray(imgKeys)) imgKeys = [];
  if (!Array.isArray(vidKeys)) vidKeys = [];

  // Parse image items (can be string or object)
  imgKeys.forEach((item: any) => {
    if (typeof item === 'string') {
      // Simple string format
      const url = item.startsWith('gs://') ? item : `gs://zghost-media-center/${gcsFolder}/${item}`;
      mediaItems.push({ url, type: 'image' });
    } else if (item && typeof item === 'object') {
      // Rich metadata object
      const artifactKey = item.artifact_key || item.name || item.filename || '';
      const url = artifactKey.startsWith('gs://')
        ? artifactKey
        : `gs://zghost-media-center/${gcsFolder}/${artifactKey}`;

      mediaItems.push({
        url,
        type: 'image',
        headline: item.headline,
        concept: item.concept,
        caption: item.caption,
        prompt: item.img_prompt || item.prompt,
        trend: item.trend,
      });
    }
  });

  // Parse video items (can be string or object)
  vidKeys.forEach((item: any) => {
    if (typeof item === 'string') {
      // Simple string format
      const url = item.startsWith('gs://') ? item : `gs://zghost-media-center/${gcsFolder}/${item}`;
      mediaItems.push({ url, type: 'video' });
    } else if (item && typeof item === 'object') {
      // Rich metadata object
      const artifactKey = item.artifact_key || item.name || item.filename || '';
      const url = artifactKey.startsWith('gs://')
        ? artifactKey
        : `gs://zghost-media-center/${gcsFolder}/${artifactKey}`;

      mediaItems.push({
        url,
        type: 'video',
        headline: item.headline,
        concept: item.concept,
        caption: item.caption,
        prompt: item.vid_prompt || item.prompt,
        trend: item.trend,
      });
    }
  });

  return mediaItems;
}

function MediaFallback({ type }: { type: 'image' | 'video' }) {
  return (
    <div className="flex flex-col items-center justify-center py-8 rounded border border-zinc-700 bg-zinc-900/50">
      <ImageOff className="w-8 h-8 text-zinc-600 mb-2" />
      <p className="text-xs text-zinc-500">
        {type === 'image' ? 'Image' : 'Video'} could not be loaded
      </p>
      <p className="text-xs text-zinc-600 mt-0.5">
        Media may require authenticated access
      </p>
    </div>
  );
}

export function ResultsGallery({ sessionState, sessionId }: ResultsGalleryProps) {
  const [expandedCopy, setExpandedCopy] = useState<number | null>(null);
  const [expandedMedia, setExpandedMedia] = useState<number | null>(null);
  const [failedMedia, setFailedMedia] = useState<Set<string>>(new Set());
  const adCopies = parseAdCopies(sessionState);
  const mediaItems = parseMediaItems(sessionState);
  const gcsFolder = sessionState.gcs_folder || '';
  const hasReport = !!sessionState.combined_final_cited_report;
  const hasVisualConcepts = !!sessionState.final_visual_concepts;

  const images = mediaItems.filter(m => m.type === 'image');
  const videos = mediaItems.filter(m => m.type === 'video');
  const totalMedia = mediaItems.length;
  const hasAny = adCopies.length > 0 || totalMedia > 0 || hasReport || hasVisualConcepts;

  const handleMediaError = (url: string) => {
    setFailedMedia(prev => new Set(prev).add(url));
  };

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
      {hasReport && (
        <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-3">
          <div className="flex items-center gap-2 mb-2">
            <FileText className="w-4 h-4 text-blue-400" />
            <span className="text-sm font-medium text-zinc-300">Research Report</span>
          </div>
          <div className="flex items-center gap-2">
            {gcsFolder && (
              <a
                href={gcsToHttpUrl(`gs://zghost-media-center/${gcsFolder}/draft_research_report_with_citations.pdf`)}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 text-xs text-blue-400 hover:text-blue-300"
              >
                <ExternalLink className="w-3 h-3" />
                View PDF Report
              </a>
            )}
            <Link
              to={`/narrative?session=${sessionId}`}
              className="flex items-center gap-1.5 text-xs text-blue-400 hover:text-blue-300 ml-auto px-2 py-1 rounded border border-blue-800/50 bg-blue-950/30 hover:bg-blue-950/50 transition-colors"
            >
              <FileText className="w-3 h-3" />
              Iterate in Narrative
            </Link>
          </div>
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
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-zinc-400">Generated Media</h3>
            {videos.length > 0 && (
              <Link
                to="/studio"
                className="flex items-center gap-1.5 text-xs text-green-400 hover:text-green-300 px-2 py-1 rounded border border-green-800/50 bg-green-950/30 hover:bg-green-950/50 transition-colors"
              >
                <Film className="w-3 h-3" />
                Open in AV Studio
              </Link>
            )}
          </div>

          {mediaItems.map((media, i) => {
            const Icon = media.type === 'video' ? Film : Image;
            const iconColor = media.type === 'video' ? 'text-green-400' : 'text-blue-400';
            const isExpanded = expandedMedia === i;

            return (
              <div key={`media-${i}`} className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-3">
                {/* Header with title and actions */}
                <div className="flex items-center gap-2 mb-2">
                  <Icon className={cn('w-4 h-4', iconColor)} />
                  <span className="text-xs text-zinc-300 truncate flex-1">
                    {media.headline || media.url.split('/').pop()}
                  </span>
                  <a
                    href={gcsToHttpUrl(media.url)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-zinc-500 hover:text-zinc-300"
                  >
                    <Download className="w-3.5 h-3.5" />
                  </a>
                  {(media.concept || media.caption || media.prompt || media.trend) && (
                    <button
                      onClick={() => setExpandedMedia(isExpanded ? null : i)}
                      className="text-zinc-500 hover:text-zinc-300"
                    >
                      <ChevronRight className={cn(
                        'w-3.5 h-3.5 transition-transform',
                        isExpanded && 'rotate-90'
                      )} />
                    </button>
                  )}
                </div>

                {/* Media Preview */}
                {failedMedia.has(media.url) ? (
                  <MediaFallback type={media.type} />
                ) : media.type === 'video' ? (
                  <video
                    src={gcsToHttpUrl(media.url)}
                    controls
                    className="w-full rounded border border-zinc-700"
                    preload="metadata"
                    onError={() => handleMediaError(media.url)}
                  />
                ) : (
                  <img
                    src={gcsToHttpUrl(media.url)}
                    alt={media.headline || `Generated ad ${i + 1}`}
                    className="w-full rounded border border-zinc-700"
                    loading="lazy"
                    onError={() => handleMediaError(media.url)}
                  />
                )}

                {/* Expandable Metadata */}
                {isExpanded && (
                  <div className="mt-3 space-y-2 border-t border-zinc-800 pt-3">
                    {media.concept && (
                      <div>
                        <span className="text-xs font-medium text-zinc-500">Concept:</span>
                        <p className="text-xs text-zinc-400 mt-0.5">{media.concept}</p>
                      </div>
                    )}
                    {media.caption && (
                      <div>
                        <span className="text-xs font-medium text-zinc-500">Caption:</span>
                        <p className="text-xs text-zinc-400 mt-0.5">{media.caption}</p>
                      </div>
                    )}
                    {media.trend && (
                      <div>
                        <span className="text-xs font-medium text-zinc-500">Trend:</span>
                        <p className="text-xs text-zinc-400 mt-0.5">{media.trend}</p>
                      </div>
                    )}
                    {media.prompt && (
                      <div>
                        <span className="text-xs font-medium text-zinc-500">Generation Prompt:</span>
                        <p className="text-xs text-zinc-400 mt-0.5 font-mono">{media.prompt}</p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
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
