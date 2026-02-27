import { http, HttpResponse } from 'msw';
import { mockSearchTrends, mockYTTrends } from './fixtures';

export const handlers = [
  // Session Management — api_server format
  http.post('*/api/v1/sessions', () => {
    return HttpResponse.json({
      session_id: 'test-session-123',
      user_id: 'default-user',
      created_at: new Date().toISOString(),
    });
  }),

  http.get('*/api/v1/sessions/:sessionId/state', () => {
    return HttpResponse.json({
      session_id: 'test-session-123',
      state: {},
    });
  }),

  http.patch('*/api/v1/sessions/:sessionId/state', () => {
    return HttpResponse.json({ status: 'success', updated_keys: [] });
  }),

  // Agent Execution — SSE stream
  http.get('*/api/v1/run/:sessionId/stream', ({ request }) => {
    const url = new URL(request.url);
    const message = url.searchParams.get('message') || '';
    const sseData = JSON.stringify({
      type: 'Event',
      data: { parts: [{ text: `Response to: ${message}` }] },
      agent_name: 'root_agent',
    });
    const completion = JSON.stringify({
      type: 'stream_complete',
      session_id: 'test-session-123',
    });
    const body = `data: ${sseData}\n\ndata: ${completion}\n\n`;
    return new HttpResponse(body, {
      headers: { 'Content-Type': 'text/event-stream' },
    });
  }),

  // Trends endpoints
  http.get('*/api/v1/trends/available', () => {
    return HttpResponse.json({
      youtube_trends: mockYTTrends,
      search_trends: mockSearchTrends,
      last_updated: new Date().toISOString(),
    });
  }),
];
