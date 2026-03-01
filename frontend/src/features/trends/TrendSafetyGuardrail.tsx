import { useState } from 'react';
import {
  ShieldCheck,
  ShieldAlert,
  ShieldX,
  ChevronDown,
  ChevronRight,
  Loader2,
  AlertTriangle,
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { api } from '../../services/api';
import type { TrendSafetyResult } from '../../services/api';
import type { SearchTrend, YTTrend } from '../../types/trends';

interface TrendSafetyGuardrailProps {
  searchTrends: SearchTrend[];
  ytTrends: YTTrend[];
  brand: string;
  targetAudience: string;
  onSafetyResults?: (results: TrendSafetyResult[], allSafe: boolean) => void;
}

export function TrendSafetyGuardrail({
  searchTrends,
  ytTrends,
  brand,
  targetAudience,
  onSafetyResults,
}: TrendSafetyGuardrailProps) {
  const [expanded, setExpanded] = useState(false);
  const [safetyLevel, setSafetyLevel] = useState<'standard' | 'strict'>('standard');
  const [results, setResults] = useState<TrendSafetyResult[]>([]);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastChecked, setLastChecked] = useState<string | null>(null);

  const totalTrends = searchTrends.length + ytTrends.length;
  const allSafe = results.length > 0 && results.every((r) => r.safe);
  const hasUnsafe = results.some((r) => r.risk_level === 'unsafe');
  const hasCaution = results.some((r) => r.risk_level === 'caution');

  const runSafetyCheck = async () => {
    if (totalTrends === 0) return;

    setChecking(true);
    setError(null);

    const trends = [
      ...searchTrends.map((t) => ({
        title: t.title,
        source: 'google_search',
        description: t.relatedQueries || '',
      })),
      ...ytTrends.map((t) => ({
        title: t.title,
        source: 'youtube',
        description: t.description || '',
      })),
    ];

    try {
      const response = await api.checkTrendSafety(
        trends,
        brand,
        targetAudience,
        safetyLevel
      );
      setResults(response.results);
      setLastChecked(new Date().toLocaleTimeString());
      onSafetyResults?.(response.results, response.overall_safe);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Safety check failed');
    } finally {
      setChecking(false);
    }
  };

  const getStatusIcon = () => {
    if (checking) return <Loader2 className="w-4 h-4 animate-spin text-blue-400" />;
    if (results.length === 0) return <ShieldCheck className="w-4 h-4 text-zinc-500" />;
    if (hasUnsafe) return <ShieldX className="w-4 h-4 text-red-400" />;
    if (hasCaution) return <ShieldAlert className="w-4 h-4 text-amber-400" />;
    return <ShieldCheck className="w-4 h-4 text-green-400" />;
  };

  const getStatusText = () => {
    if (checking) return 'Checking...';
    if (results.length === 0) return 'Not checked';
    if (hasUnsafe) return 'Issues found';
    if (hasCaution) return 'Caution';
    return 'All clear';
  };

  const getStatusColor = () => {
    if (results.length === 0) return 'border-zinc-700/50 bg-zinc-900/30';
    if (hasUnsafe) return 'border-red-800/50 bg-red-950/20';
    if (hasCaution) return 'border-amber-800/50 bg-amber-950/20';
    return 'border-green-800/50 bg-green-950/20';
  };

  return (
    <div className={cn('rounded-lg border transition-colors', getStatusColor())}>
      {/* Header - always visible */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 w-full px-3 py-2 text-left"
      >
        {getStatusIcon()}
        <span className="text-xs font-medium text-zinc-300 flex-1">
          Brand Safety Guardrail
        </span>
        <span className={cn(
          'text-[10px] px-1.5 py-0.5 rounded',
          results.length === 0
            ? 'bg-zinc-800 text-zinc-500'
            : allSafe
              ? 'bg-green-900/50 text-green-300'
              : hasUnsafe
                ? 'bg-red-900/50 text-red-300'
                : 'bg-amber-900/50 text-amber-300'
        )}>
          {getStatusText()}
        </span>
        {expanded ? (
          <ChevronDown className="w-3 h-3 text-zinc-500" />
        ) : (
          <ChevronRight className="w-3 h-3 text-zinc-500" />
        )}
      </button>

      {/* Expanded content */}
      {expanded && (
        <div className="px-3 pb-3 space-y-3">
          {/* Settings */}
          <div className="flex items-center gap-3">
            <div className="flex-1">
              <label className="text-[10px] uppercase tracking-wider text-zinc-500 block mb-1">
                Safety Level
              </label>
              <div className="flex gap-1">
                <button
                  onClick={() => setSafetyLevel('standard')}
                  className={cn(
                    'px-2 py-1 rounded text-xs transition-colors',
                    safetyLevel === 'standard'
                      ? 'bg-blue-600 text-white'
                      : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
                  )}
                >
                  Standard
                </button>
                <button
                  onClick={() => setSafetyLevel('strict')}
                  className={cn(
                    'px-2 py-1 rounded text-xs transition-colors',
                    safetyLevel === 'strict'
                      ? 'bg-blue-600 text-white'
                      : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
                  )}
                >
                  Strict
                </button>
              </div>
            </div>
            <button
              onClick={runSafetyCheck}
              disabled={checking || totalTrends === 0}
              className={cn(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors',
                totalTrends === 0
                  ? 'bg-zinc-800 text-zinc-600 cursor-not-allowed'
                  : checking
                    ? 'bg-blue-900/50 text-blue-300 cursor-wait'
                    : 'bg-blue-600 text-white hover:bg-blue-500'
              )}
            >
              {checking ? (
                <Loader2 className="w-3 h-3 animate-spin" />
              ) : (
                <ShieldCheck className="w-3 h-3" />
              )}
              {checking ? 'Checking...' : `Check ${totalTrends} Trend${totalTrends !== 1 ? 's' : ''}`}
            </button>
          </div>

          {/* Core safety notice */}
          <div className="flex items-start gap-2 p-2 rounded bg-zinc-800/50 border border-zinc-700/50">
            <AlertTriangle className="w-3 h-3 text-amber-500 flex-shrink-0 mt-0.5" />
            <p className="text-[10px] text-zinc-500 leading-relaxed">
              Core safety rules (violence, hate speech, adult content, active tragedies) cannot be overridden regardless of safety level setting.
            </p>
          </div>

          {/* Error */}
          {error && (
            <div className="p-2 rounded bg-red-950/30 border border-red-800/50">
              <p className="text-xs text-red-400">{error}</p>
            </div>
          )}

          {/* Results */}
          {results.length > 0 && (
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-[10px] uppercase tracking-wider text-zinc-500">
                  Results
                </span>
                {lastChecked && (
                  <span className="text-[10px] text-zinc-600">
                    Checked at {lastChecked}
                  </span>
                )}
              </div>
              {results.map((result, i) => (
                <div
                  key={i}
                  className={cn(
                    'flex items-start gap-2 p-2 rounded border text-xs',
                    result.risk_level === 'safe'
                      ? 'border-green-800/30 bg-green-950/10'
                      : result.risk_level === 'caution'
                        ? 'border-amber-800/30 bg-amber-950/10'
                        : 'border-red-800/30 bg-red-950/10'
                  )}
                >
                  {result.risk_level === 'safe' ? (
                    <ShieldCheck className="w-3.5 h-3.5 text-green-400 flex-shrink-0 mt-0.5" />
                  ) : result.risk_level === 'caution' ? (
                    <ShieldAlert className="w-3.5 h-3.5 text-amber-400 flex-shrink-0 mt-0.5" />
                  ) : (
                    <ShieldX className="w-3.5 h-3.5 text-red-400 flex-shrink-0 mt-0.5" />
                  )}
                  <div className="flex-1 min-w-0">
                    <p className={cn(
                      'font-medium',
                      result.risk_level === 'safe'
                        ? 'text-green-300'
                        : result.risk_level === 'caution'
                          ? 'text-amber-300'
                          : 'text-red-300'
                    )}>
                      {result.trend_title}
                    </p>
                    <p className="text-zinc-500 mt-0.5">{result.reason}</p>
                    {result.categories.length > 0 && (
                      <div className="flex gap-1 mt-1 flex-wrap">
                        {result.categories.map((cat) => (
                          <span
                            key={cat}
                            className="px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400 text-[10px]"
                          >
                            {cat}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
