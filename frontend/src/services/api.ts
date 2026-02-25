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

  // Session Management
  async createSession(appName: string, userId: string): Promise<Session> {
    return this.request<Session>(
      `/apps/${appName}/users/${userId}/sessions`,
      { method: 'POST' }
    );
  }

  async getSession(
    appName: string,
    userId: string,
    sessionId: string
  ): Promise<Session> {
    return this.request<Session>(
      `/apps/${appName}/users/${userId}/sessions/${sessionId}`
    );
  }

  async updateSessionState(
    appName: string,
    userId: string,
    sessionId: string,
    stateUpdate: Partial<Session['state']>
  ): Promise<Session> {
    return this.request<Session>(
      `/apps/${appName}/users/${userId}/sessions/${sessionId}`,
      {
        method: 'PATCH',
        body: JSON.stringify({ state: stateUpdate }),
      }
    );
  }

  // Agent Execution
  async sendMessage(payload: RunPayload): Promise<any> {
    return this.request('/run', {
      method: 'POST',
      body: JSON.stringify(payload),
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
