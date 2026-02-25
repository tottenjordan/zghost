import { useCallback } from 'react';
import type { SearchTrend, YTTrend } from '../../types/trends';

export interface TrendSelection {
  searchTrends: SearchTrend[];
  ytTrends: YTTrend[];
}

interface UseTrendsParams {
  selectedSearchTrends: SearchTrend[];
  selectedYtTrends: YTTrend[];
  setSelectedTrends: (search: SearchTrend[], yt: YTTrend[]) => void;
}

export function useTrends({
  selectedSearchTrends,
  selectedYtTrends,
  setSelectedTrends,
}: UseTrendsParams) {
  const toggleSearchTrend = useCallback((trend: SearchTrend) => {
    const isSelected = selectedSearchTrends.some((t) => t.rank === trend.rank);
    const newSearchTrends = isSelected
      ? selectedSearchTrends.filter((t) => t.rank !== trend.rank)
      : [...selectedSearchTrends, trend];

    // Immediately update the campaign store
    setSelectedTrends(newSearchTrends, selectedYtTrends);
  }, [selectedSearchTrends, selectedYtTrends, setSelectedTrends]);

  const toggleYtTrend = useCallback((trend: YTTrend) => {
    const isSelected = selectedYtTrends.some((t) => t.rank === trend.rank);
    const newYtTrends = isSelected
      ? selectedYtTrends.filter((t) => t.rank !== trend.rank)
      : [...selectedYtTrends, trend];

    // Immediately update the campaign store
    setSelectedTrends(selectedSearchTrends, newYtTrends);
  }, [selectedSearchTrends, selectedYtTrends, setSelectedTrends]);

  const clearSelections = useCallback(() => {
    setSelectedTrends([], []);
  }, [setSelectedTrends]);

  return {
    toggleSearchTrend,
    toggleYtTrend,
    clearSelections,
  };
}
