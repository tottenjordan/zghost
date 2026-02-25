import { api } from './api';
import type { DispatchConfig } from '../types/agents';

export class AgentService {
  async dispatchAgents(
    sessionId: string,
    agents: string[],
    parallel = false
  ): Promise<void> {
    const config: DispatchConfig = {
      session_id: sessionId,
      agents,
      parallel,
    };
    return api.dispatchParallel(config);
  }

  async getStatus(sessionId: string) {
    return api.getOrchestrationStatus(sessionId);
  }
}

export const agentService = new AgentService();
