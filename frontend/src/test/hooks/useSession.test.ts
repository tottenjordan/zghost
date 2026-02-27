import { describe, it, expect, beforeAll, afterEach, afterAll } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { setupServer } from 'msw/node';
import { handlers } from '../mocks/handlers';
import { useSession } from '../../hooks/useSession';

const server = setupServer(...handlers);

describe('useSession', () => {
  beforeAll(() => server.listen());
  afterEach(() => server.resetHandlers());
  afterAll(() => server.close());

  it('initializes with null session', () => {
    const { result } = renderHook(() => useSession());

    expect(result.current.sessionId).toBeNull();
    expect(result.current.state).toBeNull();
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  describe('createSession', () => {
    it('creates a new session', async () => {
      const { result } = renderHook(() => useSession());

      result.current.createSession();

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      await waitFor(() => {
        expect(result.current.sessionId).toBe('test-session-123');
      });
    });

    it('creates session with initial state', async () => {
      const { result } = renderHook(() => useSession());

      result.current.createSession({ brand: 'Google' });

      await waitFor(() => {
        expect(result.current.sessionId).not.toBeNull();
        expect(result.current.state?.brand).toBe('Google');
      });
    });
  });

  describe('loadSession', () => {
    it('loads existing session by ID', async () => {
      const { result } = renderHook(() => useSession());

      result.current.loadSession('test-session-123');

      await waitFor(() => {
        expect(result.current.sessionId).toBe('test-session-123');
        expect(result.current.state).toBeDefined();
      });
    });
  });

  describe('clearSession', () => {
    it('clears the current session', async () => {
      const { result } = renderHook(() => useSession());

      await result.current.createSession();

      await waitFor(() => {
        expect(result.current.sessionId).not.toBeNull();
      });

      result.current.clearSession();

      await waitFor(() => {
        expect(result.current.sessionId).toBeNull();
        expect(result.current.state).toBeNull();
      });
    });
  });
});
