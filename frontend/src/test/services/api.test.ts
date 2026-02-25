import { describe, it, expect, beforeAll, afterEach, afterAll } from 'vitest';
import { setupServer } from 'msw/node';
import { handlers } from '../mocks/handlers';
import { api } from '../../services/api';

const server = setupServer(...handlers);

describe('ApiClient', () => {
  beforeAll(() => server.listen());
  afterEach(() => server.resetHandlers());
  afterAll(() => server.close());

  describe('Session Management', () => {
    it('createSession generates a session ID and returns session', async () => {
      const result = await api.createSession('test-app', 'test-user');

      expect(result.session_id).toMatch(/^session_/);
      expect(result.app_name).toBe('test-app');
      expect(result.user_id).toBe('test-user');
    });

    it('getSession retrieves session by ID', async () => {
      const result = await api.getSession('test-app', 'test-user', 'session-123');

      expect(result.session_id).toBeDefined();
    });
  });

  describe('Agent Execution', () => {
    it('sendMessage constructs proper payload', async () => {
      const payload = {
        app_name: 'test-app',
        user_id: 'test-user',
        session_id: 'session-123',
        message: 'Test message',
        stream: true,
      };

      const result = await api.sendMessage(payload);

      expect(result.success).toBe(true);
      expect(result.message).toBe('Test message');
    });
  });
});
