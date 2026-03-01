import { useState, useEffect, useRef } from 'react';
import { Mic, X } from 'lucide-react';
import { useLocation } from 'react-router-dom';
import { VoiceBriefAssistant } from './VoiceBriefAssistant';
import { useVoiceSession } from './useVoiceSession';
import { useVoiceActions } from './useVoiceActions';
import { useCampaignStore } from '../../stores/campaignStore';
import { getCachedTrends } from '../../services/trendsCache';
import { cn } from '../../lib/utils';

function getSystemPromptForRoute(pathname: string): string {
  if (pathname.startsWith('/trends')) {
    return `You are a helpful marketing campaign configuration assistant. Help the user configure their campaign run: brand, product, target audience, trend selection, and rubric selection. Be concise and action-oriented.`;
  }
  if (pathname.startsWith('/orchestration')) {
    return `You are an orchestration monitoring assistant. Help the user manage jobs and orchestrations: monitor progress, interpret agent events, answer questions about the pipeline stages, and troubleshoot issues. Be concise.`;
  }
  if (pathname.startsWith('/studio')) {
    return `You are an AV Studio editing assistant. Help the user control video editing: suggest clip reordering, voice and music selection, commercial structure changes, and timing adjustments. Be concise.`;
  }
  if (pathname.startsWith('/narrative')) {
    return `You are a narrative editing assistant. Help the user make changes to the draft research report: suggest story arc adjustments, scene modifications, content improvements, and structural changes. Be concise.`;
  }
  return `You are a helpful marketing brief refinement assistant. Help users refine their marketing campaign briefs. Ask clarifying questions about target audience, campaign goals, brand voice, and key messaging. Be conversational and concise.`;
}

/** Minimized 3-bar audio visualizer for pill badge */
function MinimizedVisualizer({ isActive, isSpeaking }: { isActive: boolean; isSpeaking: boolean }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>();

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const width = 32;
    const height = 20;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.scale(dpr, dpr);

    let phase = 0;
    const barCount = 3;
    const barWidth = 3;
    const barGap = 4;

    const draw = () => {
      ctx.clearRect(0, 0, width, height);

      if (!isActive) {
        // Idle state: 3 short bars
        for (let i = 0; i < barCount; i++) {
          const x = i * (barWidth + barGap) + 8;
          const barHeight = 6;
          const y = height / 2 - barHeight / 2;

          ctx.fillStyle = 'rgba(96, 165, 250, 0.4)';
          ctx.fillRect(x, y, barWidth, barHeight);
        }
      } else {
        // Active state: animated bars
        for (let i = 0; i < barCount; i++) {
          const x = i * (barWidth + barGap) + 8;
          const t = phase + i * 0.5;

          let amplitude: number;
          if (isSpeaking) {
            amplitude = 8 + Math.abs(Math.sin(t) * Math.cos(t * 1.3)) * 6;
          } else {
            amplitude = 6 + Math.abs(Math.sin(t)) * 4;
          }

          const barHeight = Math.max(4, amplitude);
          const y = height / 2 - barHeight / 2;

          ctx.fillStyle = isSpeaking
            ? `rgba(59, 130, 246, ${0.7 + amplitude / 30})`
            : `rgba(96, 165, 250, ${0.6 + amplitude / 25})`;
          ctx.fillRect(x, y, barWidth, barHeight);
        }
        phase += isSpeaking ? 0.12 : 0.08;
      }

      animRef.current = requestAnimationFrame(draw);
    };

    draw();
    return () => {
      if (animRef.current) cancelAnimationFrame(animRef.current);
    };
  }, [isActive, isSpeaking]);

  return (
    <canvas
      ref={canvasRef}
      className="mx-1"
      style={{ width: 32, height: 20 }}
    />
  );
}

/** Compact radial audio visualizer for the expanded panel */
function FabVisualizer({ isActive, isSpeaking }: { isActive: boolean; isSpeaking: boolean }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>();

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = 48 * dpr;
    canvas.height = 48 * dpr;
    ctx.scale(dpr, dpr);

    const size = 48;
    const cx = size / 2;
    const cy = size / 2;
    const barCount = 20;
    let phase = 0;

    const draw = () => {
      ctx.clearRect(0, 0, size, size);

      if (!isActive) {
        // Subtle idle ring
        ctx.beginPath();
        ctx.arc(cx, cy, 16, 0, Math.PI * 2);
        ctx.strokeStyle = 'rgba(96, 165, 250, 0.3)';
        ctx.lineWidth = 1.5;
        ctx.stroke();
      } else {
        for (let i = 0; i < barCount; i++) {
          const angle = (i / barCount) * Math.PI * 2;
          const t = phase + (i / barCount) * Math.PI * 4;

          let amplitude: number;
          if (isSpeaking) {
            amplitude = 4 + Math.abs(Math.sin(t) * Math.cos(t * 1.7)) * 10;
          } else {
            amplitude = 3 + Math.abs(Math.sin(t)) * 6;
          }

          const innerR = 10;
          const outerR = innerR + amplitude;
          const x1 = cx + Math.cos(angle) * innerR;
          const y1 = cy + Math.sin(angle) * innerR;
          const x2 = cx + Math.cos(angle) * outerR;
          const y2 = cy + Math.sin(angle) * outerR;

          ctx.beginPath();
          ctx.moveTo(x1, y1);
          ctx.lineTo(x2, y2);
          ctx.strokeStyle = isSpeaking
            ? `rgba(59, 130, 246, ${0.6 + amplitude / 28})`
            : `rgba(96, 165, 250, ${0.5 + amplitude / 20})`;
          ctx.lineWidth = 2;
          ctx.lineCap = 'round';
          ctx.stroke();
        }
        phase += isSpeaking ? 0.08 : 0.04;
      }

      animRef.current = requestAnimationFrame(draw);
    };

    draw();
    return () => {
      if (animRef.current) cancelAnimationFrame(animRef.current);
    };
  }, [isActive, isSpeaking]);

  return (
    <canvas
      ref={canvasRef}
      style={{ width: 48, height: 48 }}
    />
  );
}

export function VoiceAssistantFAB() {
  const [isExpanded, setIsExpanded] = useState(false);
  const location = useLocation();
  const systemPrompt = getSystemPromptForRoute(location.pathname);
  const { executeAction } = useVoiceActions();
  const store = useCampaignStore();

  const {
    connectionState,
    isRecording,
    sendContext,
    isConnected,
  } = useVoiceSession({
    systemPrompt,
    onAction: executeAction,
  });

  // Send context updates when location or store state changes
  useEffect(() => {
    if (!isConnected) return;
    const cached = getCachedTrends();
    sendContext({
      page: location.pathname.replace('/', '') || 'trends',
      brand: store.config.brand,
      product: store.config.target_product,
      audience: store.config.target_audience,
      selling_points: store.config.key_selling_points,
      num_search_trends: store.selectedSearchTrends.length,
      num_yt_trends: store.selectedYtTrends.length,
      available_search_trends: cached?.searchTrends.map(t => ({ rank: t.rank, title: t.title })) || [],
      available_yt_trends: cached?.ytTrends.map(t => ({ rank: t.rank, title: t.title })) || [],
      selected_search_trend_titles: store.selectedSearchTrends.map(t => t.title),
      selected_yt_trend_titles: store.selectedYtTrends.map(t => t.title),
      active_rubric_names: store.activeRubrics.map(r => r.name),
      rubric_criteria: store.activeRubrics.flatMap(r => r.criteria.map(c => c.name)),
      commercial_duration: store.commercialDuration,
      pipeline_status: store.pipelineStatus,
    });
  }, [
    isConnected,
    sendContext,
    location.pathname,
    store.config.brand,
    store.config.target_product,
    store.config.target_audience,
    store.config.key_selling_points,
    store.selectedSearchTrends,
    store.selectedYtTrends,
    store.activeRubrics,
    store.commercialDuration,
    store.pipelineStatus,
  ]);

  return (
    <>
      {/* Expanded panel */}
      {isExpanded && (
        <div className="fixed bottom-16 right-6 z-50 w-[360px] h-[380px] shadow-2xl rounded-xl overflow-hidden border border-zinc-700">
          <div className="absolute top-2 right-2 z-10">
            <button
              onClick={() => setIsExpanded(false)}
              className="p-1.5 rounded-full bg-zinc-800/80 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-700 transition-colors"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          <VoiceBriefAssistant
            isFloating={false}
            onClose={() => setIsExpanded(false)}
          />
        </div>
      )}

      {/* Pill badge — small presence indicator with status dot and minimized visualizer */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className={cn(
          'fixed bottom-6 right-6 z-50 h-8 px-3 rounded-full shadow-lg transition-all duration-300',
          'flex items-center gap-2',
          'backdrop-blur-sm',
          'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-zinc-950',
          isExpanded
            ? 'bg-zinc-800/70 hover:bg-zinc-700/80'
            : isRecording
              ? 'bg-blue-600/80 hover:bg-blue-700/80 ring-2 ring-blue-400/50'
              : 'bg-zinc-800/60 hover:bg-zinc-700/70'
        )}
        aria-label="Voice Assistant"
      >
        {isRecording ? (
          // Show minimized visualizer when recording/speaking
          <MinimizedVisualizer
            isActive
            isSpeaking={connectionState === 'speaking'}
          />
        ) : (
          // Show mic icon + status dot when idle
          <>
            <Mic className="h-4 w-4 text-white" />
            <div
              className={cn(
                'h-2 w-2 rounded-full transition-colors',
                isConnected
                  ? 'bg-green-400 shadow-[0_0_4px_rgba(74,222,128,0.6)]'
                  : 'bg-zinc-500'
              )}
            />
          </>
        )}
      </button>
    </>
  );
}
