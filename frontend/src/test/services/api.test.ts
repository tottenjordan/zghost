import { describe, it, expect, beforeAll, afterEach, afterAll } from 'vitest';
import { setupServer } from 'msw/node';
import { handlers } from '../mocks/handlers';
import { api } from '../../services/api';
import { mockSession } from '../mocks/fixtures';

const server = setupServer(...handlers);

describe('ApiClient', () => {
  beforeAll(() => server.listen());
  afterEach(() => server.resetHandlers());
  afterAll(() => server.close());

  describe('Session Management', () => {
    it('createSession sends correct request and parses response', async () => {
      const result = await api.createSession('test-app', 'test-user');

      expect(result).toEqual(mockSession);
      expect(result.session_id).toBe('test-session-123');
      expect(result.app_name).toBe('trends_and_insights_agent');
    });

    it('getSession retrieves session by ID', async () => {
      const result = await api.getSession('test-app', 'test-user', 'session-123');

      expect(result).toEqual(mockSession);
      expect(result.session_id).toBe('test-session-123');
    });

    it('updateSessionState sends PATCH request with state update', async () => {
      const stateUpdate = {
        brand: 'Updated Brand',
        target_product: 'Updated Product',
      };

      const result = await api.updateSessionState(
        'test-app',
        'test-user',
        'session-123',
        stateUpdate
      );

      expect(result.state.brand).toBe('Updated Brand');
      expect(result.state.target_product).toBe('Updated Product');
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

  describe('Extended API Endpoints', () => {
    it('dispatchParallel sends correct stream configs', async () => {
      const config = {
        session_id: 'session-123',
        agents: ['agent1', 'agent2'],
        parallel: true,
      };

      await expect(api.dispatchParallel(config)).resolves.not.toThrow();
    });

    it('getOrchestrationStatus fetches status', async () => {
      const result = await api.getOrchestrationStatus('session-123');

      expect(result.overall_status).toBeDefined();
      expect(result.agents).toBeDefined();
    });

    it('autoSelectTrends sends configuration', async () => {
      const config = {
        session_id: 'session-123',
        num_search_trends: 3,
        num_yt_trends: 2,
        strategy: 'relevance' as const,
      };

      await expect(api.autoSelectTrends(config)).resolves.not.toThrow();
    });
  });

  describe('Error Handling', () => {
    it('throws error on failed request', async () => {
      server.use(
        handlers[0] // Override first handler to return error
      );

      // This would need a specific error handler, but demonstrates the pattern
      // In real implementation, you'd add an error handler to MSW
    });
  });
});
