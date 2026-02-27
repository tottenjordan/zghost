import { api } from './api';
import type { SessionState } from '../types/session';

export class SessionManager {
  private currentSessionId: string | null = null;
  private currentState: SessionState | null = null;

  async createSession(initialState?: Record<string, any>): Promise<{ session_id: string; user_id: string }> {
    const result = await api.createSession({ initial_state: initialState });
    this.currentSessionId = result.session_id;
    this.currentState = (initialState as SessionState) || {};
    return result;
  }

  async getSession(sessionId: string, userId?: string): Promise<{ session_id: string; state: SessionState }> {
    const result = await api.getSessionState(sessionId, userId);
    this.currentSessionId = result.session_id;
    this.currentState = result.state;
    return result;
  }

  getCurrentSessionId(): string | null {
    return this.currentSessionId;
  }

  getCurrentState(): SessionState | null {
    return this.currentState;
  }

  clearSession(): void {
    this.currentSessionId = null;
    this.currentState = null;
  }
}

export const sessionManager = new SessionManager();
