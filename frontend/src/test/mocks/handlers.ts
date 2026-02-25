import { http, HttpResponse } from 'msw';
import { mockSession, mockOrchestrationStatus, mockSearchTrends, mockYTTrends } from './fixtures';

const API_BASE = 'http://localhost:8000';

export const handlers = [
  // Session Management
  http.post(`${API_BASE}/apps/:appName/users/:userId/sessions`, () => {
    return HttpResponse.json(mockSession);
  }),

  http.get(`${API_BASE}/apps/:appName/users/:userId/sessions/:sessionId`, () => {
    return HttpResponse.json(mockSession);
  }),

  http.patch(`${API_BASE}/apps/:appName/users/:userId/sessions/:sessionId`, async ({ request }) => {
    const body = await request.json() as any;
    return HttpResponse.json({
      ...mockSession,
      state: { ...mockSession.state, ...body.state },
    });
  }),

  // Agent Execution
  http.post(`${API_BASE}/run`, async ({ request }) => {
    const body = await request.json() as any;
    return HttpResponse.json({ success: true, message: body.message });
  }),

  // Extended API endpoints
  http.post(`${API_BASE}/api/v1/dispatch`, () => {
    return HttpResponse.json({ success: true });
  }),

  http.get(`${API_BASE}/api/v1/orchestration/status`, () => {
    return HttpResponse.json(mockOrchestrationStatus);
  }),

  http.post(`${API_BASE}/api/v1/trends/auto-select`, () => {
    return HttpResponse.json({
      success: true,
      search_trends: mockSearchTrends.slice(0, 2),
      yt_trends: mockYTTrends.slice(0, 2),
      reasoning: 'Selected top trends based on relevance',
    });
  }),

  // Trend endpoints
  http.get(`${API_BASE}/api/v1/trends/search`, () => {
    return HttpResponse.json(mockSearchTrends);
  }),

  http.get(`${API_BASE}/api/v1/trends/youtube`, () => {
    return HttpResponse.json(mockYTTrends);
  }),
];
