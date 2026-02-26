import { describe, it, expect, beforeEach, beforeAll, afterEach, afterAll, vi } from 'vitest';
import { setupServer } from 'msw/node';
import { handlers } from '../mocks/handlers';
import { SessionManager } from '../../services/session';
import { mockSession } from '../mocks/fixtures';

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
    it('creates a new session and stores it', async () => {
      const session = await sessionManager.createSession('test-user');

      expect(session.session_id).toMatch(/^session_/);
      expect(session.app_name).toBe('trends_and_insights_agent');
      expect(session.user_id).toBe('test-user');
      expect(sessionManager.getCurrentSession()).toBe(session);
    });

    it('returns session with correct structure', async () => {
      const session = await sessionManager.createSession('test-user');

      expect(session.session_id).toBeDefined();
      expect(session.app_name).toBeDefined();
      expect(session.user_id).toBe('test-user');
      expect(session.state).toBeDefined();
    });
  });

  describe('getSession', () => {
    it('retrieves existing session by ID', async () => {
      const session = await sessionManager.getSession('test-user', 'session-123');

      expect(session).toEqual(mockSession);
      expect(sessionManager.getCurrentSession()).toEqual(mockSession);
    });

    it('updates current session reference', async () => {
      expect(sessionManager.getCurrentSession()).toBeNull();

      await sessionManager.getSession('test-user', 'session-123');

      expect(sessionManager.getCurrentSession()).not.toBeNull();
    });
  });

  describe('getCurrentSession', () => {
    it('returns null when no session exists', () => {
      expect(sessionManager.getCurrentSession()).toBeNull();
    });

    it('returns current session after creation', async () => {
      const session = await sessionManager.createSession('test-user');

      expect(sessionManager.getCurrentSession()).toBe(session);
      expect(session.app_name).toBe('trends_and_insights_agent');
      expect(session.user_id).toBe('test-user');
    });
  });

  describe('clearSession', () => {
    it('clears the current session', async () => {
      await sessionManager.createSession('test-user');
      expect(sessionManager.getCurrentSession()).not.toBeNull();

      sessionManager.clearSession();

      expect(sessionManager.getCurrentSession()).toBeNull();
    });
  });
});
