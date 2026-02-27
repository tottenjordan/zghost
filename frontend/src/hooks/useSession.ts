import { useState, useCallback } from 'react';
import { sessionManager } from '../services/session';
import type { SessionState } from '../types/session';

export function useSession() {
  const [sessionId, setSessionId] = useState<string | null>(
    sessionManager.getCurrentSessionId()
  );
  const [state, setState] = useState<SessionState | null>(
    sessionManager.getCurrentState()
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const createSession = useCallback(async (initialState?: Record<string, any>) => {
    setLoading(true);
    setError(null);
    try {
      const result = await sessionManager.createSession(initialState);
      setSessionId(result.session_id);
      setState((initialState as SessionState) || {});
      return result;
    } catch (err) {
      setError(err as Error);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const loadSession = useCallback(
    async (id: string, userId?: string) => {
      setLoading(true);
      setError(null);
      try {
        const result = await sessionManager.getSession(id, userId);
        setSessionId(result.session_id);
        setState(result.state);
        return result;
      } catch (err) {
        setError(err as Error);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const clearSession = useCallback(() => {
    sessionManager.clearSession();
    setSessionId(null);
    setState(null);
  }, []);

  return {
    sessionId,
    state,
    loading,
    error,
    createSession,
    loadSession,
    clearSession,
  };
}
