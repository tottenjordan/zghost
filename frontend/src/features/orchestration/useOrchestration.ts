import { useState, useCallback, useEffect, useRef } from 'react';
import { useAgentStatus } from '../../hooks/useAgentStatus';
import { useStreaming } from '../../hooks/useStreaming';
import { api } from '../../services/api';
import { parseAgentEvent } from '../../services/streaming';
import type { AgentEvent, AgentEventType } from '../../types/agents';

const POLLING_INTERVAL = 5000;

export interface FilterOptions {
  agentName?: string;
  eventType?: AgentEventType;
  searchTerm?: string;
}

export function useOrchestration(sessionId: string | null, streamUrl: string | null) {
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [filters, setFilters] = useState<FilterOptions>({});
  const [isPaused, setIsPaused] = useState(false);
  const [sessionState, setSessionState] = useState<Record<string, any>>({});
  const [changedKeys, setChangedKeys] = useState<Set<string>>(new Set());
  const previousStateRef = useRef<Record<string, any>>({});

  // Get orchestration status via polling
  const { status, loading, error: statusError, refetch } = useAgentStatus(sessionId);

  // Get event stream
  const {
    events: streamEvents,
    isConnected,
    error: streamError,
    clearEvents,
    seedEvents,
    addEvent,
  } = useStreaming(streamUrl);

  // Hydrate events from server when session exists but no live stream
  const hydratedRef = useRef<string | null>(null);
  useEffect(() => {
    // Reset hydration ref when sessionId becomes null (user navigates away)
    if (!sessionId) {
      hydratedRef.current = null;
      return;
    }

    // Don't hydrate if we have a live stream or already hydrated this session
    if (streamUrl || hydratedRef.current === sessionId) return;

    hydratedRef.current = sessionId;
    api.getSessionEvents(sessionId).then((result) => {
      if (result.events.length > 0) {
        const parsed = result.events.map(parseAgentEvent);
        seedEvents(parsed);
      }
    }).catch(() => {
      // Session events not available — that's OK
    });
  }, [sessionId, streamUrl, seedEvents]);

  // Poll session state (not events — events come from SSE stream)
  useEffect(() => {
    if (!sessionId) return;

    const pollState = async () => {
      try {
        const result = await api.getSessionState(sessionId);
        const currentState = result.state || {};
        setSessionState(currentState);

        const changed = new Set<string>();
        const prevState = previousStateRef.current;

        Object.keys(currentState).forEach(key => {
          const currentVal = (currentState as Record<string, any>)[key];
          const prevVal = (prevState as Record<string, any>)[key];
          if (JSON.stringify(currentVal) !== JSON.stringify(prevVal)) {
            changed.add(key);
          }
        });

        setChangedKeys(changed);
        previousStateRef.current = currentState;

        // Clear changed keys after 3 seconds
        setTimeout(() => {
          setChangedKeys(new Set());
        }, 3000);
      } catch (err) {
        console.warn('Session state polling failed:', err);
      }
    };

    pollState();
    const interval = setInterval(pollState, POLLING_INTERVAL);
    return () => clearInterval(interval);
  }, [sessionId]);

  // Events come from the SSE stream
  const allEvents = streamEvents;

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
    addEvent,
    isConnected,

    // Session state
    sessionState,
    changedKeys,

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
