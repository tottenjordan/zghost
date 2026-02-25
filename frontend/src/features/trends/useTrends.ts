import { useState, useCallback, useEffect } from 'react';
import type { SearchTrend, YTTrend } from '../../types/trends';
import type { Session } from '../../types/session';

export interface TrendSelection {
  searchTrends: SearchTrend[];
  ytTrends: YTTrend[];
}

export function useTrends(session: Session | null) {
  const [selectedSearchTrends, setSelectedSearchTrends] = useState<SearchTrend[]>([]);
  const [selectedYtTrends, setSelectedYtTrends] = useState<YTTrend[]>([]);
  const [autoSelecting, setAutoSelecting] = useState(false);

  // Load trends from session state on mount
  useEffect(() => {
    if (session?.state) {
      if (session.state.target_search_trends?.target_search_trends) {
        setSelectedSearchTrends(session.state.target_search_trends.target_search_trends);
      }
      if (session.state.target_yt_trends?.target_yt_trends) {
        setSelectedYtTrends(session.state.target_yt_trends.target_yt_trends);
      }
    }
  }, [session]);

  const toggleSearchTrend = useCallback((trend: SearchTrend) => {
    setSelectedSearchTrends((prev) => {
      const isSelected = prev.some((t) => t.rank === trend.rank);
      if (isSelected) {
        return prev.filter((t) => t.rank !== trend.rank);
      }
      return [...prev, trend];
    });
  }, []);

  const toggleYtTrend = useCallback((trend: YTTrend) => {
    setSelectedYtTrends((prev) => {
      const isSelected = prev.some((t) => t.rank === trend.rank);
      if (isSelected) {
        return prev.filter((t) => t.rank !== trend.rank);
      }
      return [...prev, trend];
    });
  }, []);

  const clearSelections = useCallback(() => {
    setSelectedSearchTrends([]);
    setSelectedYtTrends([]);
  }, []);

  return {
    selectedSearchTrends,
    selectedYtTrends,
    setSelectedSearchTrends,
    setSelectedYtTrends,
    toggleSearchTrend,
    toggleYtTrend,
    autoSelecting,
    clearSelections,
  };
}
