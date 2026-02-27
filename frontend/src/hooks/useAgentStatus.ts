import { useState, useCallback, useEffect, useRef } from 'react';
import { api } from '../services/api';
import type { OrchestrationStatus } from '../types/agents';

export function useAgentStatus(sessionId: string | null, pollingInterval = 3000) {
  const [status, setStatus] = useState<OrchestrationStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const hasLoggedError = useRef(false);

  const fetchStatus = useCallback(async () => {
    if (!sessionId) return;

    setLoading(true);
    try {
      const result = await api.getSessionState(sessionId);
      const state = result.state || {};

      // Map session state to OrchestrationStatus format
      const agentStates: Record<string, any> = {};

      // Infer agent status from session state keys
      const agentNames = [
        'root_agent', 'trends_and_insights_agent', 'research_orchestrator',
        'ad_content_generator_agent', 'av_editing_studio_agent',
      ];
      for (const name of agentNames) {
        agentStates[name] = {
          status: state._state_init ? 'running' : 'idle',
          lastUpdate: new Date().toISOString(),
        };
      }

      // Check for completion signals in state
      if (state.combined_final_cited_report) {
        agentStates['research_orchestrator'] = { status: 'completed' };
      }
      if (state.final_select_ad_copies?.final_select_ad_copies?.length > 0) {
        agentStates['ad_content_generator_agent'] = { status: 'completed' };
      }

      setStatus({
        sessionId,
        pipelineStatus: 'running',
        agents: agentStates,
        startedAt: new Date().toISOString(),
      });
      setError(null);
      hasLoggedError.current = false;
    } catch (err) {
      // Suppress repeated errors to avoid console spam
      if (!hasLoggedError.current) {
        console.warn('Session polling failed (suppressing further warnings):', (err as Error).message);
        hasLoggedError.current = true;
      }
      // Don't set error for polling failures — the pipeline may still be running
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    if (!sessionId) return;

    fetchStatus();
    const interval = setInterval(fetchStatus, pollingInterval);
    return () => clearInterval(interval);
  }, [sessionId, pollingInterval, fetchStatus]);

  return {
    status,
    loading,
    error,
    refetch: fetchStatus,
  };
}
