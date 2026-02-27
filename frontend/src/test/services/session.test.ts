import { describe, it, expect, beforeEach, beforeAll, afterEach, afterAll } from 'vitest';
import { setupServer } from 'msw/node';
import { handlers } from '../mocks/handlers';
import { SessionManager } from '../../services/session';

const server = setupServer(...handlers);

describe('SessionManager', () => {
  let sessionManager: SessionManager;

  beforeAll(() => server.listen());
  afterEach(() => {
    server.resetHandlers();
    sessionManager.clearSession();
  });
  afterAll(() => server.close());

  beforeEach(() => {
    sessionManager = new SessionManager();
  });

  describe('createSession', () => {
    it('creates a new session and stores session ID', async () => {
      const result = await sessionManager.createSession();

      expect(result.session_id).toBe('test-session-123');
      expect(result.user_id).toBe('default-user');
      expect(sessionManager.getCurrentSessionId()).toBe('test-session-123');
    });

    it('creates session with initial state', async () => {
      const result = await sessionManager.createSession({ brand: 'Google' });

      expect(result.session_id).toBeDefined();
      expect(sessionManager.getCurrentState()?.brand).toBe('Google');
    });
  });

  describe('getSession', () => {
    it('retrieves existing session state by ID', async () => {
      const result = await sessionManager.getSession('test-session-123');

      expect(result.session_id).toBe('test-session-123');
      expect(result.state).toBeDefined();
      expect(sessionManager.getCurrentSessionId()).toBe('test-session-123');
    });
  });

  describe('getCurrentSessionId', () => {
    it('returns null when no session exists', () => {
      expect(sessionManager.getCurrentSessionId()).toBeNull();
    });

    it('returns session ID after creation', async () => {
      await sessionManager.createSession();
      expect(sessionManager.getCurrentSessionId()).toBe('test-session-123');
    });
  });

  describe('clearSession', () => {
    it('clears the current session', async () => {
      await sessionManager.createSession();
      expect(sessionManager.getCurrentSessionId()).not.toBeNull();

      sessionManager.clearSession();

      expect(sessionManager.getCurrentSessionId()).toBeNull();
      expect(sessionManager.getCurrentState()).toBeNull();
    });
  });
});
