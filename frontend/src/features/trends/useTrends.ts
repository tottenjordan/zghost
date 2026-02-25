import { useState, useCallback, useEffect } from 'react';
import { api } from '../../services/api';
import type { SearchTrend, YTTrend, AutoSelectConfig } from '../../types/trends';
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

  const autoSelectTrends = useCallback(
    async (config: Omit<AutoSelectConfig, 'session_id'>) => {
      if (!session?.session_id) {
        throw new Error('No active session');
      }

      setAutoSelecting(true);
      try {
        await api.autoSelectTrends({
          ...config,
          session_id: session.session_id,
        });
        // Refresh session to get updated trends
        // This would typically trigger a session reload
      } finally {
        setAutoSelecting(false);
      }
    },
    [session]
  );

  const clearSelections = useCallback(() => {
    setSelectedSearchTrends([]);
    setSelectedYtTrends([]);
  }, []);

  return {
    selectedSearchTrends,
    selectedYtTrends,
    toggleSearchTrend,
    toggleYtTrend,
    autoSelectTrends,
    autoSelecting,
    clearSelections,
  };
}
