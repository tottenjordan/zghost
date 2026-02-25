import { useState, useCallback } from 'react';
import { sessionManager } from '../services/session';
import type { Session } from '../types/session';

export function useSession() {
  const [session, setSession] = useState<Session | null>(
    sessionManager.getCurrentSession()
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const createSession = useCallback(async (userId: string) => {
    setLoading(true);
    setError(null);
    try {
      const newSession = await sessionManager.createSession(userId);
      setSession(newSession);
      return newSession;
    } catch (err) {
      setError(err as Error);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const loadSession = useCallback(
    async (userId: string, sessionId: string) => {
      setLoading(true);
      setError(null);
      try {
        const loadedSession = await sessionManager.getSession(userId, sessionId);
        setSession(loadedSession);
        return loadedSession;
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
    setSession(null);
  }, []);

  return {
    session,
    loading,
    error,
    createSession,
    loadSession,
    clearSession,
  };
}
