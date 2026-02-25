import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import type { SearchTrend, YTTrend } from '../../types/trends';

interface TrendCompareProps {
  availableSearchTrends: SearchTrend[];
  availableYtTrends: YTTrend[];
}

type ComparableTrend = (SearchTrend | YTTrend) & { type: 'search' | 'youtube' };

export function TrendCompare({
  availableSearchTrends,
  availableYtTrends,
}: TrendCompareProps) {
  const [selectedForCompare, setSelectedForCompare] = useState<ComparableTrend[]>([]);

  const allTrends: ComparableTrend[] = [
    ...availableSearchTrends.map((t) => ({ ...t, type: 'search' as const })),
    ...availableYtTrends.map((t) => ({ ...t, type: 'youtube' as const })),
  ];

  const toggleCompare = (trend: ComparableTrend) => {
    setSelectedForCompare((prev) => {
      const isSelected = prev.some((t) => t.rank === trend.rank && t.type === trend.type);
      if (isSelected) {
        return prev.filter((t) => !(t.rank === trend.rank && t.type === trend.type));
      }
      if (prev.length >= 3) {
        return prev;
      }
      return [...prev, trend];
    });
  };

  const clearCompare = () => {
    setSelectedForCompare([]);
  };

  if (allTrends.length === 0) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Compare Trends</CardTitle>
          {selectedForCompare.length > 0 && (
            <div className="flex items-center gap-2">
              <Badge variant="info">
                {selectedForCompare.length} / 3 selected
              </Badge>
              <Button size="sm" variant="ghost" onClick={clearCompare}>
                Clear
              </Button>
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {selectedForCompare.length < 2 ? (
          <div>
            <p className="mb-4 text-sm text-zinc-400">
              Select 2-3 trends from your selections to compare side by side
            </p>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {allTrends.slice(0, 6).map((trend) => (
                <button
                  key={`${trend.type}-${trend.rank}`}
                  onClick={() => toggleCompare(trend)}
                  disabled={
                    selectedForCompare.length >= 3 &&
                    !selectedForCompare.some(
                      (t) => t.rank === trend.rank && t.type === trend.type
                    )
                  }
                  className={`rounded-lg border p-3 text-left text-sm transition-all ${
                    selectedForCompare.some(
                      (t) => t.rank === trend.rank && t.type === trend.type
                    )
                      ? 'border-blue-500 bg-blue-950/20'
                      : 'border-zinc-800 bg-zinc-900/50 hover:border-zinc-700'
                  } disabled:opacity-50`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <span className="line-clamp-2 font-medium">
                      {trend.title}
                    </span>
                    <Badge variant={trend.type === 'search' ? 'info' : 'success'}>
                      {trend.type === 'search' ? 'GS' : 'YT'}
                    </Badge>
                  </div>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-800">
                  <th className="pb-3 text-left font-medium text-zinc-300">Metric</th>
                  {selectedForCompare.map((trend) => (
                    <th
                      key={`${trend.type}-${trend.rank}`}
                      className="pb-3 pl-4 text-left font-medium text-zinc-300"
                    >
                      <Badge
                        variant={trend.type === 'search' ? 'info' : 'success'}
                        className="mb-1"
                      >
                        {trend.type === 'search' ? 'Google' : 'YouTube'}
                      </Badge>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-zinc-800">
                  <td className="py-3 text-zinc-400">Title</td>
                  {selectedForCompare.map((trend) => (
                    <td
                      key={`${trend.type}-${trend.rank}-title`}
                      className="py-3 pl-4"
                    >
                      {trend.title}
                    </td>
                  ))}
                </tr>
                <tr className="border-b border-zinc-800">
                  <td className="py-3 text-zinc-400">Rank</td>
                  {selectedForCompare.map((trend) => (
                    <td
                      key={`${trend.type}-${trend.rank}-rank`}
                      className="py-3 pl-4"
                    >
                      #{trend.rank}
                    </td>
                  ))}
                </tr>
                <tr className="border-b border-zinc-800">
                  <td className="py-3 text-zinc-400">Engagement</td>
                  {selectedForCompare.map((trend) => (
                    <td
                      key={`${trend.type}-${trend.rank}-engagement`}
                      className="py-3 pl-4"
                    >
                      {trend.type === 'search'
                        ? (trend as SearchTrend).formattedTraffic
                        : (trend as YTTrend).viewCount}
                    </td>
                  ))}
                </tr>
                <tr>
                  <td className="py-3 text-zinc-400">Source</td>
                  {selectedForCompare.map((trend) => (
                    <td
                      key={`${trend.type}-${trend.rank}-source`}
                      className="py-3 pl-4 text-xs text-zinc-500"
                    >
                      {trend.type === 'search'
                        ? (trend as SearchTrend).relatedQueries
                        : (trend as YTTrend).channelName}
                    </td>
                  ))}
                </tr>
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
