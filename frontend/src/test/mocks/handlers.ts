import { http, HttpResponse } from 'msw';
import { mockSession, mockOrchestrationStatus, mockSearchTrends, mockYTTrends } from './fixtures';

export const handlers = [
  // Session Management
  http.post('*/apps/:appName/users/:userId/sessions', () => {
    return HttpResponse.json(mockSession);
  }),

  http.get('*/apps/:appName/users/:userId/sessions/:sessionId', () => {
    return HttpResponse.json(mockSession);
  }),

  http.patch('*/apps/:appName/users/:userId/sessions/:sessionId', async ({ request }) => {
    const body = await request.json() as any;
    return HttpResponse.json({
      ...mockSession,
      state: { ...mockSession.state, ...body.state },
    });
  }),

  // Agent Execution (ADK format: new_message.parts[0].text)
  http.post('*/run', async ({ request }) => {
    const body = await request.json() as any;
    const text = body.newMessage?.parts?.[0]?.text ?? body.new_message?.parts?.[0]?.text ?? body.message;
    return HttpResponse.json({ success: true, message: text });
  }),

  // Extended API endpoints
  http.post('*/api/v1/dispatch', () => {
    return HttpResponse.json({ success: true });
  }),

  http.get('*/api/v1/orchestration/status', () => {
    return HttpResponse.json(mockOrchestrationStatus);
  }),

  http.post('*/api/v1/trends/auto-select', () => {
    return HttpResponse.json({
      success: true,
      search_trends: mockSearchTrends.slice(0, 2),
      yt_trends: mockYTTrends.slice(0, 2),
      reasoning: 'Selected top trends based on relevance',
    });
  }),

  // Trend endpoints
  http.get('*/api/v1/trends/search', () => {
    return HttpResponse.json(mockSearchTrends);
  }),

  http.get('*/api/v1/trends/youtube', () => {
    return HttpResponse.json(mockYTTrends);
  }),
];
