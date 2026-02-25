import { http, HttpResponse } from 'msw';
import { mockSession, mockSearchTrends, mockYTTrends } from './fixtures';

export const handlers = [
  // Session Management
  http.post('*/apps/:appName/users/:userId/sessions', () => {
    return HttpResponse.json(mockSession);
  }),

  http.post('*/apps/:appName/users/:userId/sessions/:sessionId', () => {
    return HttpResponse.json(mockSession);
  }),

  http.get('*/apps/:appName/users/:userId/sessions/:sessionId', () => {
    return HttpResponse.json(mockSession);
  }),

  // Agent Execution (ADK api_server /run format)
  http.post('*/run', async ({ request }) => {
    const body = await request.json() as any;
    const text = body.newMessage?.parts?.[0]?.text ?? body.new_message?.parts?.[0]?.text ?? body.message;
    return HttpResponse.json({ success: true, message: text });
  }),

  // Trend endpoints (used by trendsCache)
  http.get('*/api/v1/trends/search', () => {
    return HttpResponse.json(mockSearchTrends);
  }),

  http.get('*/api/v1/trends/youtube', () => {
    return HttpResponse.json(mockYTTrends);
  }),
];
