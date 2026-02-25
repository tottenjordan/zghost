import type { RunPayload, Session } from '../types/session';
import type { DispatchConfig, OrchestrationStatus } from '../types/agents';
import type { AutoSelectConfig } from '../types/trends';

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
      throw new Error(`API request failed: ${response.statusText}`);
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

  // Session Management
  // ADK api_server creates sessions implicitly on first /run call.
  // We generate a session ID client-side and create the session via POST with initial state.
  async createSession(appName: string, userId: string): Promise<Session> {
    const sessionId = `session_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
    await this.request(
      `/apps/${appName}/users/${userId}/sessions/${sessionId}`,
      { method: 'POST', body: JSON.stringify({}) }
    );
    return { session_id: sessionId, app_name: appName, user_id: userId, created_at: new Date().toISOString(), state: {} as Session['state'] };
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

  async updateSessionState(
    appName: string,
    userId: string,
    sessionId: string,
    stateUpdate: Partial<Session['state']>
  ): Promise<Session> {
    const adkResponse = await this.request<any>(
      `/apps/${appName}/users/${userId}/sessions/${sessionId}`,
      {
        method: 'PATCH',
        body: JSON.stringify({ state: stateUpdate }),
      }
    );
    return this.mapSession(adkResponse);
  }

  // Agent Execution — ADK api_server /run format (camelCase)
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

  // Streaming execution via SSE
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

  // Extended API endpoints
  async dispatchParallel(config: DispatchConfig): Promise<void> {
    return this.request('/api/v1/dispatch', {
      method: 'POST',
      body: JSON.stringify(config),
    });
  }

  async getOrchestrationStatus(
    sessionId: string
  ): Promise<OrchestrationStatus> {
    return this.request(`/api/v1/orchestration/status?session_id=${sessionId}`);
  }

  async autoSelectTrends(config: AutoSelectConfig): Promise<void> {
    return this.request('/api/v1/trends/auto-select', {
      method: 'POST',
      body: JSON.stringify(config),
    });
  }
}

export const api = new ApiClient();
