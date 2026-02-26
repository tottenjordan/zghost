import type { RunPayload, Session } from '../types/session';

const API_BASE = import.meta.env.VITE_API_BASE || '';

class ApiClient {
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${API_BASE}${endpoint}`;
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      throw new Error(`API request failed (${response.status}): ${response.statusText || 'Unknown error'}`);
    }

    return response.json();
  }

  private mapSession(adkResponse: any): Session {
    return {
      session_id: adkResponse.id,
      app_name: adkResponse.appName,
      user_id: adkResponse.userId,
      created_at: adkResponse.createdAt || new Date().toISOString(),
      state: adkResponse.state || {},
      events: adkResponse.events || [],
    };
  }

  async createSession(appName: string, userId: string): Promise<Session> {
    const sessionId = `session_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
    await this.request(
      `/apps/${appName}/users/${userId}/sessions/${sessionId}`,
      { method: 'POST', body: JSON.stringify({}) }
    );
    return {
      session_id: sessionId,
      app_name: appName,
      user_id: userId,
      created_at: new Date().toISOString(),
      state: {} as Session['state'],
    };
  }

  async getSession(
    appName: string,
    userId: string,
    sessionId: string
  ): Promise<Session> {
    const adkResponse = await this.request<any>(
      `/apps/${appName}/users/${userId}/sessions/${sessionId}`
    );
    return this.mapSession(adkResponse);
  }

  async sendMessage(payload: RunPayload): Promise<any> {
    const adkPayload = {
      appName: payload.app_name,
      userId: payload.user_id,
      sessionId: payload.session_id,
      newMessage: {
        role: 'user',
        parts: [{ text: payload.message }],
      },
      streaming: payload.stream ?? false,
    };
    return this.request('/run', {
      method: 'POST',
      body: JSON.stringify(adkPayload),
    });
  }

  async sendMessageSSE(payload: RunPayload): Promise<Response> {
    const adkPayload = {
      appName: payload.app_name,
      userId: payload.user_id,
      sessionId: payload.session_id,
      newMessage: {
        role: 'user',
        parts: [{ text: payload.message }],
      },
      streaming: true,
    };
    const url = `${API_BASE}/run_sse`;
    return fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(adkPayload),
    });
  }
}

export const api = new ApiClient();
