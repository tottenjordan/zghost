import { useState, useCallback, useEffect, useRef } from 'react';
import { agentService } from '../services/agents';
import type { OrchestrationStatus } from '../types/agents';

export function useAgentStatus(sessionId: string | null, pollingInterval = 2000) {
  const [status, setStatus] = useState<OrchestrationStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const hasLoggedError = useRef(false);

  const fetchStatus = useCallback(async () => {
    if (!sessionId) return;

    setLoading(true);
    try {
      const newStatus = await agentService.getStatus(sessionId);
      setStatus(newStatus);
      setError(null);
      hasLoggedError.current = false;
    } catch (err) {
      // Only log the first error to avoid console spam when backend is down
      if (!hasLoggedError.current) {
        console.warn('Agent status polling failed (suppressing further warnings):', (err as Error).message);
        hasLoggedError.current = true;
      }
      setError(err as Error);
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
