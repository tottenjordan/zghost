import type { SessionState } from '../types/session';

const API_BASE = import.meta.env.VITE_API_BASE || '';

export interface SessionCreateOptions {
  preset_config?: string;
  initial_state?: Record<string, any>;
}

export interface SessionCreateResult {
  session_id: string;
  user_id: string;
  created_at: string;
}

export interface SessionStateResult {
  session_id: string;
  state: SessionState;
}

class ApiClient {
  /**
   * Create a new session on api_server.
   * Optionally pass a preset_config name or initial_state to preload.
   */
  async createSession(
    options: SessionCreateOptions = {}
  ): Promise<SessionCreateResult> {
    const url = `${API_BASE}/api/v1/sessions`;
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(options),
    });
    if (!response.ok) {
      throw new Error(
        `API request failed (${response.status}): ${response.statusText || 'Unknown error'}`
      );
    }
    return response.json();
  }

  /**
   * Get session state from api_server.
   */
  async getSessionState(
    sessionId: string,
    userId = 'default-user'
  ): Promise<SessionStateResult> {
    const params = new URLSearchParams({ user_id: userId });
    const url = `${API_BASE}/api/v1/sessions/${sessionId}/state?${params}`;
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(
        `API request failed (${response.status}): ${response.statusText || 'Unknown error'}`
      );
    }
    return response.json();
  }

  /**
   * Update specific session state keys.
   */
  async updateSessionState(
    sessionId: string,
    updates: Record<string, any>,
    userId = 'default-user'
  ): Promise<void> {
    const params = new URLSearchParams({ user_id: userId });
    const url = `${API_BASE}/api/v1/sessions/${sessionId}/state?${params}`;
    const response = await fetch(url, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ updates }),
    });
    if (!response.ok) {
      throw new Error(
        `API request failed (${response.status}): ${response.statusText || 'Unknown error'}`
      );
    }
  }

  /**
   * Send a message to the agent and wait for the SSE stream to complete.
   * Returns the last text response from the agent.
   */
  async sendMessage(
    sessionId: string,
    message: string,
    userId = 'default-user'
  ): Promise<string> {
    const params = new URLSearchParams({ user_id: userId, message });
    const url = `${API_BASE}/api/v1/run/${sessionId}/stream?${params}`;
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(
        `API request failed (${response.status}): ${response.statusText || 'Unknown error'}`
      );
    }

    // Consume SSE stream and collect text responses
    const reader = response.body!.getReader();
    const decoder = new TextDecoder();
    let lastText = '';
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const event = JSON.parse(line.slice(6));
            if (event.data?.parts) {
              for (const part of event.data.parts) {
                if (part.text) lastText = part.text;
              }
            }
          } catch {
            // Skip malformed SSE events
          }
        }
      }
    }

    return lastText;
  }

  /**
   * Build an SSE stream URL for a message.
   * Use with EventSource or fetch for real-time event streaming.
   */
  getStreamUrl(
    sessionId: string,
    message: string,
    userId = 'default-user'
  ): string {
    const params = new URLSearchParams({ user_id: userId, message });
    return `${API_BASE}/api/v1/run/${sessionId}/stream?${params}`;
  }
}

export const api = new ApiClient();
