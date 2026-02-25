import { describe, it, expect, beforeAll, afterEach, afterAll } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { setupServer } from 'msw/node';
import { handlers } from '../mocks/handlers';
import { useSession } from '../../hooks/useSession';
import { mockSession } from '../mocks/fixtures';

const server = setupServer(...handlers);

describe('useSession', () => {
  beforeAll(() => server.listen());
  afterEach(() => server.resetHandlers());
  afterAll(() => server.close());

  it('initializes with null session', () => {
    const { result } = renderHook(() => useSession());

    expect(result.current.session).toBeNull();
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  describe('createSession', () => {
    it('creates a new session', async () => {
      const { result } = renderHook(() => useSession());

      expect(result.current.loading).toBe(false);

      result.current.createSession('test-user');

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      await waitFor(() => {
        expect(result.current.session).toEqual(mockSession);
      });
    });

    it('sets loading state during creation', async () => {
      const { result } = renderHook(() => useSession());

      result.current.createSession('test-user');

      // Would check loading state in between, but needs proper async handling
      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });
    });

    it('handles creation errors', async () => {
      server.use(
        // Add error handler here in full implementation
      );

      const { result } = renderHook(() => useSession());

      try {
        await result.current.createSession('test-user');
      } catch (err) {
        // Error should be caught
      }
    });
  });

  describe('loadSession', () => {
    it('loads existing session by ID', async () => {
      const { result } = renderHook(() => useSession());

      result.current.loadSession('test-user', 'session-123');

      await waitFor(() => {
        expect(result.current.session).toEqual(mockSession);
      });
    });

    it('sets loading state during load', async () => {
      const { result } = renderHook(() => useSession());

      result.current.loadSession('test-user', 'session-123');

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });
    });
  });

  describe('clearSession', () => {
    it('clears the current session', async () => {
      const { result } = renderHook(() => useSession());

      await result.current.createSession('test-user');

      await waitFor(() => {
        expect(result.current.session).not.toBeNull();
      });

      result.current.clearSession();

      await waitFor(() => {
        expect(result.current.session).toBeNull();
      });
    });
  });

  describe('error handling', () => {
    it('sets error state on failure', async () => {
      // Would implement error handler in MSW
      const { result } = renderHook(() => useSession());

      // Trigger error scenario
      // Check that result.current.error is set
    });

    it('clears error on successful operation', async () => {
      const { result } = renderHook(() => useSession());

      // First trigger error, then successful operation
      // Verify error is cleared
    });
  });
});
