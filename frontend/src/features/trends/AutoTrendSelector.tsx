import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Slider } from '../../components/ui/Slider';
import { Spinner } from '../../components/ui/Spinner';
import { Badge } from '../../components/ui/Badge';
import { SearchTrendCard, YTTrendCard } from './TrendCard';
import { Shield, AlertTriangle, XCircle } from 'lucide-react';
import type { SearchTrend, YTTrend } from '../../types/trends';
import type { BrandSafetyResult } from '../../services/brandSafety';

interface AutoTrendSelectorProps {
  loading: boolean;
  onAutoSelect: (config: {
    num_search_trends: number;
    num_yt_trends: number;
    strategy?: 'top' | 'diverse' | 'relevance';
  }) => void;
  autoSelectedSearchTrends?: SearchTrend[];
  autoSelectedYtTrends?: YTTrend[];
  aiReasoning?: string;
  safetyResult?: BrandSafetyResult;
  onAccept?: () => void;
  onReject?: () => void;
}

export function AutoTrendSelector({
  loading,
  onAutoSelect,
  autoSelectedSearchTrends = [],
  autoSelectedYtTrends = [],
  aiReasoning,
  safetyResult,
  onAccept,
  onReject,
}: AutoTrendSelectorProps) {
  const [numSearchTrends, setNumSearchTrends] = useState(3);
  const [numYtTrends, setNumYtTrends] = useState(3);
  const [strategy, setStrategy] = useState<'top' | 'diverse' | 'relevance'>('relevance');

  const handleAutoSelect = () => {
    onAutoSelect({
      num_search_trends: numSearchTrends,
      num_yt_trends: numYtTrends,
      strategy,
    });
  };

  const hasResults =
    autoSelectedSearchTrends.length > 0 || autoSelectedYtTrends.length > 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <svg
            className="h-5 w-5 text-yellow-400"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
          </svg>
          AI Auto-Selection
        </CardTitle>
      </CardHeader>
      <CardContent>
        {!hasResults ? (
          <div className="space-y-6">
            <div>
              <div className="mb-2 flex items-center justify-between">
                <label className="text-sm font-medium text-zinc-300">
                  Google Search Trends
                </label>
                <span className="text-sm text-zinc-400">{numSearchTrends}</span>
              </div>
              <Slider
                min={1}
                max={10}
                step={1}
                value={numSearchTrends}
                onChange={(e) => setNumSearchTrends(Number(e.target.value))}
              />
            </div>

            <div>
              <div className="mb-2 flex items-center justify-between">
                <label className="text-sm font-medium text-zinc-300">
                  YouTube Trends
                </label>
                <span className="text-sm text-zinc-400">{numYtTrends}</span>
              </div>
              <Slider
                min={1}
                max={10}
                step={1}
                value={numYtTrends}
                onChange={(e) => setNumYtTrends(Number(e.target.value))}
              />
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium text-zinc-300">
                Selection Strategy
              </label>
              <div className="grid grid-cols-3 gap-2">
                <Button
                  variant={strategy === 'top' ? 'primary' : 'secondary'}
                  size="sm"
                  onClick={() => setStrategy('top')}
                >
                  Top Ranked
                </Button>
                <Button
                  variant={strategy === 'diverse' ? 'primary' : 'secondary'}
                  size="sm"
                  onClick={() => setStrategy('diverse')}
                >
                  Diverse
                </Button>
                <Button
                  variant={strategy === 'relevance' ? 'primary' : 'secondary'}
                  size="sm"
                  onClick={() => setStrategy('relevance')}
                >
                  Relevance
                </Button>
              </div>
            </div>

            <Button
              onClick={handleAutoSelect}
              disabled={loading}
              className="w-full"
            >
              {loading ? (
                <>
                  <Spinner size="sm" className="mr-2" />
                  Analyzing trends...
                </>
              ) : (
                'Auto-Select Trends'
              )}
            </Button>
          </div>
        ) : (
          <div className="space-y-4">
            {aiReasoning && (
              <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-4">
                <h4 className="mb-2 text-sm font-semibold text-zinc-300">
                  AI Reasoning
                </h4>
                <p className="text-sm text-zinc-400">{aiReasoning}</p>
              </div>
            )}

            {safetyResult && (
              <SafetySummary safetyResult={safetyResult} />
            )}

            <div>
              <h4 className="mb-3 text-sm font-semibold text-zinc-300">
                Selected Google Search Trends ({autoSelectedSearchTrends.length})
              </h4>
              <div className="grid gap-3 sm:grid-cols-2">
                {autoSelectedSearchTrends.map((trend) => {
                  const safetyScore = safetyResult?.searchTrendScores.find(
                    (s) => s.trendTitle === trend.title
                  );
                  return (
                    <SearchTrendCard
                      key={trend.rank}
                      trend={trend}
                      selected={true}
                      onToggle={() => {}}
                      safetyScore={safetyScore}
                    />
                  );
                })}
              </div>
            </div>

            {autoSelectedYtTrends.length > 0 && (
              <div>
                <h4 className="mb-3 text-sm font-semibold text-zinc-300">
                  Selected YouTube Trends ({autoSelectedYtTrends.length})
                </h4>
                <div className="grid gap-3 sm:grid-cols-2">
                  {autoSelectedYtTrends.map((trend) => {
                    const safetyScore = safetyResult?.ytTrendScores.find(
                      (s) => s.trendTitle === trend.title
                    );
                    return (
                      <YTTrendCard
                        key={trend.rank}
                        trend={trend}
                        selected={true}
                        onToggle={() => {}}
                        safetyScore={safetyScore}
                      />
                    );
                  })}
                </div>
              </div>
            )}

            <div className="flex gap-2">
              <Button onClick={onAccept} className="flex-1">
                Accept All
              </Button>
              <Button onClick={onReject} variant="secondary" className="flex-1">
                Modify Selection
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function SafetySummary({ safetyResult }: { safetyResult: BrandSafetyResult }) {
  const allScores = [
    ...safetyResult.searchTrendScores,
    ...safetyResult.ytTrendScores,
  ];

  const safeCount = allScores.filter((s) => s.level === 'safe').length;
  const cautionCount = allScores.filter((s) => s.level === 'caution').length;
  const unsafeCount = allScores.filter((s) => s.level === 'unsafe').length;
  const totalCount = allScores.length;

  if (totalCount === 0) return null;

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-4">
      <div className="mb-3 flex items-center gap-2">
        <Shield className="h-4 w-4 text-blue-400" />
        <h4 className="text-sm font-semibold text-zinc-300">
          Brand Safety Summary
        </h4>
      </div>
      <div className="flex flex-wrap gap-2">
        {safeCount > 0 && (
          <Badge variant="success" className="flex items-center gap-1">
            <Shield className="h-3 w-3" />
            {safeCount} Safe
          </Badge>
        )}
        {cautionCount > 0 && (
          <Badge variant="warning" className="flex items-center gap-1">
            <AlertTriangle className="h-3 w-3" />
            {cautionCount} Caution
          </Badge>
        )}
        {unsafeCount > 0 && (
          <Badge variant="error" className="flex items-center gap-1">
            <XCircle className="h-3 w-3" />
            {unsafeCount} Filtered (Unsafe)
          </Badge>
        )}
      </div>
      {unsafeCount > 0 && (
        <p className="mt-2 text-xs text-amber-400">
          Unsafe trends have been automatically filtered out from the selection.
        </p>
      )}
    </div>
  );
}
