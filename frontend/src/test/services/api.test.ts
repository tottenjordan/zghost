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
    it('createSession returns session_id and user_id', async () => {
      const result = await api.createSession();

      expect(result.session_id).toBe('test-session-123');
      expect(result.user_id).toBe('default-user');
    });

    it('getSessionState retrieves session state', async () => {
      const result = await api.getSessionState('test-session-123');

      expect(result.session_id).toBe('test-session-123');
      expect(result.state).toBeDefined();
    });
  });

  describe('Agent Execution', () => {
    it('sendMessage consumes SSE stream and returns text', async () => {
      const result = await api.sendMessage('test-session-123', 'Test message');

      expect(result).toContain('Test message');
    });
  });
});
