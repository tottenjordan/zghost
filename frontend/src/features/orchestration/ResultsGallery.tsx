import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Image,
  Film,
  FileText,
  ExternalLink,
  Download,
  ChevronRight,
  ChevronDown,
  ImageOff,
  CheckCircle2,
  Circle,
  PenLine,
  MessageSquare,
  Sparkles,
} from 'lucide-react';
import { Badge } from '../../components/ui/Badge';
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

function parseAdCopies(raw: any): AdCopy[] {
  if (!raw) return [];
  const copies = raw.final_select_ad_copies || raw.ad_copy_draft || raw;
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

  imgKeys.forEach((item: any) => {
    if (typeof item === 'string') {
      const url = item.startsWith('gs://') ? item : `gs://zghost-media-center/${gcsFolder}/${item}`;
      mediaItems.push({ url, type: 'image' });
    } else if (item && typeof item === 'object') {
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

  vidKeys.forEach((item: any) => {
    if (typeof item === 'string') {
      const url = item.startsWith('gs://') ? item : `gs://zghost-media-center/${gcsFolder}/${item}`;
      mediaItems.push({ url, type: 'video' });
    } else if (item && typeof item === 'object') {
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

/** Check if a headline matches between draft candidates and selected items */
function isSelected(candidate: AdCopy, selectedCopies: AdCopy[]): boolean {
  if (!candidate.headline) return false;
  return selectedCopies.some(
    (s) => s.headline && s.headline.toLowerCase() === candidate.headline!.toLowerCase()
  );
}

function MediaFallback({ type }: { type: 'image' | 'video' }) {
  return (
    <div className="flex flex-col items-center justify-center py-8 rounded border border-zinc-700 bg-zinc-900/50">
      <ImageOff className="w-8 h-8 text-zinc-600 mb-2" />
      <p className="text-xs text-zinc-500">
        {type === 'image' ? 'Image' : 'Video'} could not be loaded
      </p>
    </div>
  );
}

/** Collapsible section with step indicator */
function PipelineStep({
  step,
  title,
  icon: Icon,
  iconColor,
  status,
  children,
  defaultOpen = false,
}: {
  step: number;
  title: string;
  icon: typeof PenLine;
  iconColor: string;
  status: 'pending' | 'done';
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className={cn(
      'rounded-lg border transition-colors',
      status === 'done' ? 'border-zinc-700/50 bg-zinc-900/30' : 'border-zinc-800/50 bg-zinc-950/30 opacity-60'
    )}>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 w-full px-3 py-2 text-left"
      >
        <span className={cn(
          'flex items-center justify-center w-5 h-5 rounded-full text-[10px] font-bold flex-shrink-0',
          status === 'done' ? 'bg-green-950/50 text-green-400 border border-green-800/50' : 'bg-zinc-800 text-zinc-500 border border-zinc-700'
        )}>
          {step}
        </span>
        <Icon className={cn('w-3.5 h-3.5 flex-shrink-0', iconColor)} />
        <span className="text-xs font-medium text-zinc-300 flex-1">{title}</span>
        {status === 'done' && (
          <CheckCircle2 className="w-3.5 h-3.5 text-green-500 flex-shrink-0" />
        )}
        {open ? (
          <ChevronDown className="w-3 h-3 text-zinc-500" />
        ) : (
          <ChevronRight className="w-3 h-3 text-zinc-500" />
        )}
      </button>
      {open && <div className="px-3 pb-3">{children}</div>}
    </div>
  );
}

export function ResultsGallery({ sessionState, sessionId }: ResultsGalleryProps) {
  const [expandedMedia, setExpandedMedia] = useState<number | null>(null);
  const [failedMedia, setFailedMedia] = useState<Set<string>>(new Set());

  const gcsFolder = sessionState.gcs_folder || '';

  // Ad copy pipeline
  const draftCopies = parseAdCopies(sessionState.ad_copy_draft);
  const selectedCopies = parseAdCopies(sessionState.final_select_ad_copies);
  const hasCritique = !!sessionState.ad_copy_critique;

  // Visual concept pipeline
  const hasVisualDraft = !!sessionState.visual_draft;
  const hasVisualCritique = !!sessionState.visual_concept_critique;
  const hasFinalVisuals = !!sessionState.final_visual_concepts;
  const hasVisualSelection = !!sessionState.final_select_vis_concepts;

  // Research
  const hasReport = !!sessionState.combined_final_cited_report;
  const draftPdfUrl = sessionState.draft_pdf_url;
  const finalPdfUrl = sessionState.final_pdf_url;
  const pdfUrl = finalPdfUrl || draftPdfUrl || (gcsFolder ? `gs://zghost-media-center/${gcsFolder}/draft_research_report_with_citations.pdf` : '');

  // Media
  const mediaItems = parseMediaItems(sessionState);
  const images = mediaItems.filter(m => m.type === 'image');
  const videos = mediaItems.filter(m => m.type === 'video');

  // Commercial
  const hasCommercial = !!(
    sessionState.commercial_artifact &&
    (typeof sessionState.commercial_artifact === 'string' || sessionState.commercial_artifact.artifact_key)
  );

  const hasAny = draftCopies.length > 0 || selectedCopies.length > 0 || hasReport || hasVisualDraft || mediaItems.length > 0;

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
        <Badge variant={selectedCopies.length > 0 ? 'success' : draftCopies.length > 0 ? 'info' : 'default'} className="text-xs">
          {selectedCopies.length > 0 ? `${selectedCopies.length} Ad Copies` : draftCopies.length > 0 ? 'Drafting...' : 'Ad Copy Pending'}
        </Badge>
        <Badge variant={hasVisualSelection ? 'success' : hasFinalVisuals ? 'info' : 'default'} className="text-xs">
          Visuals {hasVisualSelection ? 'Selected' : hasFinalVisuals ? 'Finalized' : 'Pending'}
        </Badge>
        <Badge variant={mediaItems.length > 0 ? 'success' : 'default'} className="text-xs">
          {mediaItems.length} Media
        </Badge>
        {hasCommercial && (
          <Badge variant="success" className="text-xs">Commercial Ready</Badge>
        )}
      </div>

      {/* ── RESEARCH ── */}
      {hasReport && (
        <div className="rounded-lg border border-blue-800/30 bg-blue-950/10 p-3">
          <div className="flex items-center gap-2 mb-2">
            <FileText className="w-4 h-4 text-blue-400" />
            <span className="text-sm font-medium text-zinc-300">Research Report</span>
          </div>
          <div className="flex items-center gap-2">
            {pdfUrl && (
              <a
                href={gcsToHttpUrl(pdfUrl)}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 text-xs text-blue-400 hover:text-blue-300"
              >
                <ExternalLink className="w-3 h-3" />
                View PDF
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

      {/* ── AD COPY PIPELINE ── */}
      {(draftCopies.length > 0 || selectedCopies.length > 0) && (
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-zinc-300 flex items-center gap-2">
            <PenLine className="w-4 h-4 text-purple-400" />
            Ad Copy Pipeline
          </h3>

          {/* Step 1: Draft */}
          {draftCopies.length > 0 && (
            <PipelineStep
              step={1}
              title={`Draft Candidates (${draftCopies.length})`}
              icon={PenLine}
              iconColor="text-purple-400"
              status="done"
              defaultOpen={selectedCopies.length === 0}
            >
              <div className="space-y-1.5">
                {draftCopies.map((copy, i) => {
                  const selected = isSelected(copy, selectedCopies);
                  return (
                    <div
                      key={i}
                      className={cn(
                        'flex items-start gap-2 p-2 rounded border text-xs',
                        selected
                          ? 'border-green-700/50 bg-green-950/20'
                          : 'border-zinc-800 bg-zinc-900/30'
                      )}
                    >
                      {selected ? (
                        <CheckCircle2 className="w-4 h-4 text-green-400 flex-shrink-0 mt-0.5" />
                      ) : (
                        <Circle className="w-4 h-4 text-zinc-600 flex-shrink-0 mt-0.5" />
                      )}
                      <div className="flex-1 min-w-0">
                        <p className={cn('font-medium', selected ? 'text-green-300' : 'text-zinc-300')}>
                          {copy.headline || `Option ${i + 1}`}
                        </p>
                        {copy.body && (
                          <p className="text-zinc-500 mt-0.5 line-clamp-2">{copy.body}</p>
                        )}
                        {copy.cta && (
                          <p className="text-blue-400 mt-0.5">CTA: {copy.cta}</p>
                        )}
                      </div>
                      {copy.score && (
                        <span className={cn(
                          'text-[10px] font-medium px-1.5 py-0.5 rounded',
                          selected ? 'bg-green-900/50 text-green-300' : 'bg-zinc-800 text-zinc-400'
                        )}>
                          {copy.score}
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            </PipelineStep>
          )}

          {/* Step 2: Critique */}
          <PipelineStep
            step={2}
            title="Critique & Scoring"
            icon={MessageSquare}
            iconColor="text-amber-400"
            status={hasCritique ? 'done' : 'pending'}
          >
            {hasCritique ? (
              <p className="text-xs text-zinc-400">
                {typeof sessionState.ad_copy_critique === 'string'
                  ? sessionState.ad_copy_critique.slice(0, 300) + '...'
                  : 'Critique completed — scores applied to candidates above'}
              </p>
            ) : (
              <p className="text-xs text-zinc-500">Waiting for critique agent...</p>
            )}
          </PipelineStep>

          {/* Step 3: Selection */}
          <PipelineStep
            step={3}
            title={`Selected (${selectedCopies.length})`}
            icon={CheckCircle2}
            iconColor="text-green-400"
            status={selectedCopies.length > 0 ? 'done' : 'pending'}
            defaultOpen={selectedCopies.length > 0}
          >
            {selectedCopies.length > 0 ? (
              <div className="space-y-1.5">
                {selectedCopies.map((copy, i) => (
                  <div key={i} className="p-2 rounded border border-green-700/40 bg-green-950/15">
                    <p className="text-xs font-medium text-green-300">{copy.headline}</p>
                    {copy.body && <p className="text-xs text-zinc-400 mt-0.5">{copy.body}</p>}
                    {copy.cta && <p className="text-xs text-blue-400 mt-0.5">CTA: {copy.cta}</p>}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-zinc-500">Waiting for selection...</p>
            )}
          </PipelineStep>
        </div>
      )}

      {/* ── VISUAL CONCEPT PIPELINE ── */}
      {(hasVisualDraft || hasFinalVisuals) && (
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-zinc-300 flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-amber-400" />
            Visual Concept Pipeline
          </h3>

          <PipelineStep
            step={1}
            title="Visual Concept Drafts"
            icon={PenLine}
            iconColor="text-amber-400"
            status={hasVisualDraft ? 'done' : 'pending'}
          >
            <p className="text-xs text-zinc-400">
              {typeof sessionState.visual_draft === 'string'
                ? sessionState.visual_draft.slice(0, 300) + '...'
                : 'Draft concepts generated'}
            </p>
          </PipelineStep>

          <PipelineStep
            step={2}
            title="Visual Critique"
            icon={MessageSquare}
            iconColor="text-amber-400"
            status={hasVisualCritique ? 'done' : 'pending'}
          >
            <p className="text-xs text-zinc-400">
              {typeof sessionState.visual_concept_critique === 'string'
                ? sessionState.visual_concept_critique.slice(0, 300) + '...'
                : hasVisualCritique ? 'Critique completed' : 'Waiting...'}
            </p>
          </PipelineStep>

          <PipelineStep
            step={3}
            title="Finalized Concepts"
            icon={Sparkles}
            iconColor="text-green-400"
            status={hasFinalVisuals ? 'done' : 'pending'}
            defaultOpen={hasFinalVisuals && !hasVisualSelection}
          >
            <p className="text-xs text-zinc-400">
              {typeof sessionState.final_visual_concepts === 'string'
                ? sessionState.final_visual_concepts.slice(0, 300) + '...'
                : hasFinalVisuals ? 'Concepts finalized' : 'Waiting...'}
            </p>
          </PipelineStep>
        </div>
      )}

      {/* ── GENERATED MEDIA ── */}
      {(images.length > 0 || videos.length > 0) && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-zinc-300 flex items-center gap-2">
              <Film className="w-4 h-4 text-green-400" />
              Generated Media ({mediaItems.length})
            </h3>
            {videos.length > 0 && (
              <Link
                to={`/studio?session=${sessionId}`}
                className="flex items-center gap-1.5 text-xs text-green-400 hover:text-green-300 px-2 py-1 rounded border border-green-800/50 bg-green-950/30 hover:bg-green-950/50 transition-colors"
              >
                <Film className="w-3 h-3" />
                AV Studio
              </Link>
            )}
          </div>

          {mediaItems.map((media, i) => {
            const Icon = media.type === 'video' ? Film : Image;
            const iconColor = media.type === 'video' ? 'text-green-400' : 'text-blue-400';
            const isExpanded = expandedMedia === i;

            return (
              <div key={`media-${i}`} className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-3">
                <div className="flex items-center gap-2 mb-2">
                  <Icon className={cn('w-4 h-4', iconColor)} />
                  <span className="text-xs text-zinc-300 truncate flex-1">
                    {media.headline || media.url.split('/').pop()}
                  </span>
                  {media.type === 'image' && (
                    <Link
                      to={`/studio?session=${sessionId}`}
                      className="text-xs text-blue-400 hover:text-blue-300"
                      title="Open in AV Studio"
                    >
                      <Film className="w-3 h-3" />
                    </Link>
                  )}
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

      {/* GCS Folder */}
      {gcsFolder && (
        <div className="text-xs text-zinc-600 pt-2 border-t border-zinc-800">
          GCS: gs://zghost-media-center/{gcsFolder}/
        </div>
      )}
    </div>
  );
}
