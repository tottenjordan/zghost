import { api } from './api';
import type { Session } from '../types/session';

const APP_NAME = import.meta.env.VITE_APP_NAME || 'trends_and_insights_agent';

export class SessionManager {
  private currentSession: Session | null = null;

  async createSession(userId: string): Promise<Session> {
    this.currentSession = await api.createSession(APP_NAME, userId);
    return this.currentSession;
  }

  async getSession(userId: string, sessionId: string): Promise<Session> {
    this.currentSession = await api.getSession(APP_NAME, userId, sessionId);
    return this.currentSession;
  }

  getCurrentSession(): Session | null {
    return this.currentSession;
  }

  clearSession(): void {
    this.currentSession = null;
  }
}

export const sessionManager = new SessionManager();
