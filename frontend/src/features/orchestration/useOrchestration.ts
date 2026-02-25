import { useState, useCallback, useEffect, useRef } from 'react';
import { useAgentStatus } from '../../hooks/useAgentStatus';
import { useStreaming } from '../../hooks/useStreaming';
import { api } from '../../services/api';
import type { AgentEvent, AgentEventType } from '../../types/agents';
import type { SessionEvent } from '../../types/session';

const APP_NAME = import.meta.env.VITE_APP_NAME || 'trends_and_insights_agent';
const USER_ID = 'frontend-user';
const POLLING_INTERVAL = 5000;

export interface FilterOptions {
  agentName?: string;
  eventType?: AgentEventType;
  searchTerm?: string;
}

function parseSessionEvents(events: SessionEvent[]): AgentEvent[] {
  return events.map((event, index) => {
    const author = event.author || 'unknown';
    const agentName = author.startsWith('user') ? 'user' : author;
    const timestamp = Date.now() - (events.length - index) * 1000;

    // Determine event type from content
    let type: AgentEventType = 'agent_step';
    if (event.content?.role === 'user') {
      type = 'agent_start';
    } else if (event.actions?.stateDelta) {
      type = 'agent_step';
    }

    return {
      type,
      agentName,
      timestamp,
      data: {
        content: event.content?.parts?.[0]?.text,
        stateDelta: event.actions?.stateDelta,
        invocationId: event.invocationId,
      },
    };
  });
}

export function useOrchestration(sessionId: string | null, streamUrl: string | null) {
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [filters, setFilters] = useState<FilterOptions>({});
  const [isPaused, setIsPaused] = useState(false);
  const [sessionEvents, setSessionEvents] = useState<AgentEvent[]>([]);
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
  } = useStreaming(streamUrl);

  // Poll session for events and state
  useEffect(() => {
    if (!sessionId) return;

    const pollSession = async () => {
      try {
        const session = await api.getSession(APP_NAME, USER_ID, sessionId);

        // Parse events from session
        if (session.events && session.events.length > 0) {
          const parsed = parseSessionEvents(session.events);
          setSessionEvents(parsed);
        }

        // Track state changes
        const currentState = session.state || {};
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
        console.warn('Session polling failed:', err);
      }
    };

    pollSession();
    const interval = setInterval(pollSession, POLLING_INTERVAL);
    return () => clearInterval(interval);
  }, [sessionId]);

  // Merge session events with stream events
  const allEvents = [...sessionEvents, ...streamEvents];

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
