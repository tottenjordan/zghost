import { useState, useEffect } from 'react';
import { api } from '../../services/api';
import { Markdown } from '../../components/ui/Markdown';
import { cn } from '../../lib/utils';
import { Users, TrendingUp, AlertTriangle, CheckCircle2, XCircle, Loader2 } from 'lucide-react';

interface FocusGroupResultsProps {
  sessionId: string;
}

interface CategoryScore {
  name: string;
  score: number;
  weight: number;
}

const CATEGORIES: { name: string; weight: number }[] = [
  { name: 'Visual Quality', weight: 20 },
  { name: 'Narrative Consistency', weight: 20 },
  { name: 'Trend Relevance', weight: 15 },
  { name: 'Product Integration', weight: 15 },
  { name: 'Emotional Impact', weight: 15 },
  { name: 'Audience Appeal', weight: 15 },
];

function parseScores(text: string): CategoryScore[] {
  const scores: CategoryScore[] = [];

  for (const cat of CATEGORIES) {
    // Match patterns like "| Visual Quality | 8 |" or "Visual Quality: 8/10"
    const patterns = [
      new RegExp(`\\|\\s*${cat.name}\\s*\\|\\s*(\\d+\\.?\\d*)`, 'gi'),
      new RegExp(`${cat.name}[:\\s]+(\\d+\\.?\\d*)\\s*/\\s*10`, 'gi'),
      new RegExp(`${cat.name}.*?:\\s*(\\d+\\.?\\d*)`, 'gi'),
    ];

    const allMatches: number[] = [];
    for (const pattern of patterns) {
      let match;
      while ((match = pattern.exec(text)) !== null) {
        const val = parseFloat(match[1]);
        if (val >= 1 && val <= 10) allMatches.push(val);
      }
    }

    if (allMatches.length > 0) {
      const avg = allMatches.reduce((a, b) => a + b, 0) / allMatches.length;
      scores.push({ name: cat.name, score: avg, weight: cat.weight });
    }
  }

  return scores;
}

function parseOverallScore(text: string): number | null {
  // Look for patterns like "Overall Commercial Score: 8.2/10" or "weighted average: 8.2"
  const patterns = [
    /overall\s+(?:commercial\s+)?score[:\s]+(\d+\.?\d*)\s*(?:\/\s*10)?/i,
    /weighted\s+average[:\s]+(\d+\.?\d*)/i,
    /overall\s+score[:\s]+(\d+\.?\d*)/i,
  ];

  for (const pattern of patterns) {
    const match = text.match(pattern);
    if (match) {
      const val = parseFloat(match[1]);
      if (val >= 1 && val <= 10) return val;
    }
  }

  return null;
}

function parseGoNoGo(text: string): 'go' | 'no-go' | null {
  if (/recommendation\s+is\s+\*?\*?GO\*?\*?[.\s]/i.test(text) && !/NO-GO/i.test(text.match(/recommendation\s+is\s+\*?\*?(GO|NO-GO)\*?\*?/i)?.[0] || '')) {
    return 'go';
  }
  if (/NO-GO/i.test(text)) return 'no-go';
  if (/\bGO\b/.test(text) && !/NO-GO/i.test(text)) return 'go';
  return null;
}

function parseUplift(text: string): string | null {
  const match = text.match(/uplift\s+potential[:\s]+\*?\*?(Low|Medium|High|Very High)\*?\*?/i);
  return match ? match[1] : null;
}

function scoreColor(score: number): string {
  if (score >= 8) return 'text-green-400';
  if (score >= 6) return 'text-yellow-400';
  return 'text-red-400';
}

function scoreBgColor(score: number): string {
  if (score >= 8) return 'bg-green-500';
  if (score >= 6) return 'bg-yellow-500';
  return 'bg-red-500';
}

function scoreTrackColor(score: number): string {
  if (score >= 8) return 'bg-green-950/50';
  if (score >= 6) return 'bg-yellow-950/50';
  return 'bg-red-950/50';
}

export function FocusGroupResults({ sessionId }: FocusGroupResultsProps) {
  const [focusGroupText, setFocusGroupText] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!sessionId) return;

    const fetchEvents = async () => {
      setLoading(true);
      try {
        const result = await api.getSessionEvents(sessionId);
        // Find focus group agent response text
        let bestText = '';
        for (const event of result.events) {
          if (
            event.agentName === 'focus_group_evaluator_agent' &&
            event.data?.parts
          ) {
            for (const part of event.data.parts) {
              if (part.text && part.text.length > bestText.length) {
                bestText = part.text;
              }
            }
          }
        }
        setFocusGroupText(bestText || null);
      } catch {
        setFocusGroupText(null);
      } finally {
        setLoading(false);
      }
    };

    fetchEvents();
  }, [sessionId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-5 h-5 animate-spin text-zinc-500 mr-2" />
        <span className="text-sm text-zinc-500">Loading focus group results...</span>
      </div>
    );
  }

  if (!focusGroupText) {
    return (
      <div className="rounded-lg border border-zinc-700 bg-zinc-800 p-8 text-center">
        <Users className="w-8 h-8 text-zinc-600 mx-auto mb-3" />
        <p className="text-zinc-400 text-sm">
          No focus group evaluation found for this run.
        </p>
        <p className="text-zinc-600 text-xs mt-1">
          Focus group results appear after the pipeline completes.
        </p>
      </div>
    );
  }

  const scores = parseScores(focusGroupText);
  const overallScore = parseOverallScore(focusGroupText);
  const goNoGo = parseGoNoGo(focusGroupText);
  const uplift = parseUplift(focusGroupText);

  // Calculate weighted overall if not parsed directly
  const computedOverall =
    overallScore ??
    (scores.length > 0
      ? scores.reduce((sum, s) => sum + s.score * s.weight, 0) /
        scores.reduce((sum, s) => sum + s.weight, 0)
      : null);

  return (
    <div className="space-y-4">
      {/* Overall Score Card */}
      {computedOverall !== null && (
        <div className="flex items-center gap-4 rounded-lg border border-zinc-800 bg-zinc-900/50 p-4">
          {/* Big score */}
          <div className="flex flex-col items-center justify-center w-20 h-20 rounded-xl bg-zinc-800 border border-zinc-700">
            <span className={cn('text-2xl font-bold', scoreColor(computedOverall))}>
              {computedOverall.toFixed(1)}
            </span>
            <span className="text-[10px] text-zinc-500">/10</span>
          </div>

          <div className="flex-1">
            <h3 className="text-sm font-semibold text-zinc-200">Focus Group Score</h3>
            <p className="text-xs text-zinc-500 mt-0.5">
              Weighted average across {scores.length} categories, 5 panelists
            </p>
          </div>

          {/* Go/No-Go badge */}
          {goNoGo && (
            <div
              className={cn(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-sm font-semibold',
                goNoGo === 'go'
                  ? 'bg-green-950/30 border-green-700 text-green-400'
                  : 'bg-red-950/30 border-red-700 text-red-400'
              )}
            >
              {goNoGo === 'go' ? (
                <CheckCircle2 className="w-4 h-4" />
              ) : (
                <XCircle className="w-4 h-4" />
              )}
              {goNoGo === 'go' ? 'GO' : 'NO-GO'}
            </div>
          )}

          {/* Uplift badge */}
          {uplift && (
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-blue-700 bg-blue-950/30 text-blue-400 text-xs font-medium">
              <TrendingUp className="w-3.5 h-3.5" />
              {uplift} Uplift
            </div>
          )}
        </div>
      )}

      {/* Category Score Bars */}
      {scores.length > 0 && (
        <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-4 space-y-3">
          <h4 className="text-xs font-medium text-zinc-400 uppercase tracking-wide mb-2">
            Category Breakdown
          </h4>
          {scores.map((cat) => (
            <div key={cat.name} className="space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-sm text-zinc-300">
                  {cat.name}
                  <span className="ml-1.5 text-[10px] text-zinc-600">({cat.weight}%)</span>
                </span>
                <span className={cn('text-sm font-semibold', scoreColor(cat.score))}>
                  {cat.score.toFixed(1)}
                </span>
              </div>
              <div className={cn('h-2 rounded-full overflow-hidden', scoreTrackColor(cat.score))}>
                <div
                  className={cn('h-full rounded-full transition-all', scoreBgColor(cat.score))}
                  style={{ width: `${(cat.score / 10) * 100}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Full Report */}
      <details className="rounded-lg border border-zinc-800 bg-zinc-900/50">
        <summary className="px-4 py-3 cursor-pointer text-sm font-medium text-zinc-300 hover:text-zinc-100 select-none">
          <span className="ml-1">Full Focus Group Report</span>
        </summary>
        <div className="px-4 pb-4 border-t border-zinc-800 pt-3 max-h-[60vh] overflow-y-auto">
          <Markdown content={focusGroupText} />
        </div>
      </details>
    </div>
  );
}
