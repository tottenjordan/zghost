import { useState, useCallback } from 'react';
import { useAgentStatus } from '../../hooks/useAgentStatus';
import { useStreaming } from '../../hooks/useStreaming';
import type { AgentEvent, AgentEventType } from '../../types/agents';

export interface FilterOptions {
  agentName?: string;
  eventType?: AgentEventType;
  searchTerm?: string;
}

export function useOrchestration(sessionId: string | null, streamUrl: string | null) {
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [filters, setFilters] = useState<FilterOptions>({});
  const [isPaused, setIsPaused] = useState(false);

  // Get orchestration status via polling
  const { status, loading, error: statusError, refetch } = useAgentStatus(sessionId);

  // Get event stream
  const {
    events: allEvents,
    isConnected,
    error: streamError,
    clearEvents,
  } = useStreaming(streamUrl);

  // Filter events based on current filter options
  const filteredEvents = useCallback(() => {
    let filtered = allEvents;

    if (filters.agentName) {
      filtered = filtered.filter((e) => e.agentName === filters.agentName);
    }

    if (filters.eventType) {
      filtered = filtered.filter((e) => e.type === filters.eventType);
    }

    if (filters.searchTerm) {
      const term = filters.searchTerm.toLowerCase();
      filtered = filtered.filter((e) => {
        const dataStr = JSON.stringify(e.data).toLowerCase();
        return (
          e.agentName.toLowerCase().includes(term) ||
          e.type.toLowerCase().includes(term) ||
          dataStr.includes(term)
        );
      });
    }

    return filtered;
  }, [allEvents, filters]);

  // Get events for selected agent
  const getAgentEvents = useCallback(
    (agentName: string): AgentEvent[] => {
      return allEvents.filter((e) => e.agentName === agentName);
    },
    [allEvents]
  );

  // Update filters
  const updateFilters = useCallback((newFilters: Partial<FilterOptions>) => {
    setFilters((prev) => ({ ...prev, ...newFilters }));
  }, []);

  const clearFilters = useCallback(() => {
    setFilters({});
  }, []);

  // Toggle pause for auto-scroll
  const togglePause = useCallback(() => {
    setIsPaused((prev) => !prev);
  }, []);

  return {
    // Status
    status,
    loading,
    error: statusError || streamError,
    refetch,

    // Events
    events: filteredEvents(),
    allEvents,
    getAgentEvents,
    clearEvents,
    isConnected,

    // Filters
    filters,
    updateFilters,
    clearFilters,

    // UI state
    selectedAgent,
    setSelectedAgent,
    isPaused,
    togglePause,
  };
}
