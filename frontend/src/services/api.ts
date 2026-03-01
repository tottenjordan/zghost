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

export interface SessionSummary {
  session_id: string;
  user_id: string;
  last_update_time: number;
  brand?: string;
  target_product?: string;
  target_audience?: string;
  commercial_duration?: number;
  autopilot_mode?: boolean;
  status?: string;
  has_report: boolean;
  has_commercial: boolean;
  has_images: boolean;
  has_videos: boolean;
  image_count: number;
  video_count: number;
}

export interface SessionListResult {
  sessions: SessionSummary[];
  total: number;
}

export interface TrendSafetyResult {
  trend_title: string;
  safe: boolean;
  risk_level: 'safe' | 'caution' | 'unsafe';
  reason: string;
  categories: string[];
}

export interface TrendSafetyCheckResponse {
  results: TrendSafetyResult[];
  overall_safe: boolean;
  checked_at: string;
  model_used: string;
}

export interface NarrativeRefineResult {
  refined_text: string;
  direction_applied: string;
}

export interface NarrativePdfResult {
  pdf_url: string;
  gcs_uri: string;
}

class ApiClient {
  /**
   * List all sessions from the Vertex session service.
   */
  async listSessions(userId = 'default-user'): Promise<SessionListResult> {
    const params = new URLSearchParams({ user_id: userId });
    const url = `${API_BASE}/api/v1/sessions?${params}`;
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(
        `API request failed (${response.status}): ${response.statusText || 'Unknown error'}`
      );
    }
    return response.json();
  }

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
   * Fetch stored SSE events for a session (for hydrating timeline on revisit).
   */
  async getSessionEvents(
    sessionId: string
  ): Promise<{ session_id: string; events: any[]; total_events: number }> {
    const url = `${API_BASE}/api/v1/orchestration/${sessionId}/events`;
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(
        `API request failed (${response.status}): ${response.statusText || 'Unknown error'}`
      );
    }
    return response.json();
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

  /**
   * Refine narrative text using a lightweight Gemini call (not the full pipeline).
   */
  async refineNarrative(
    sessionId: string,
    direction: string,
    currentText?: string
  ): Promise<NarrativeRefineResult> {
    const url = `${API_BASE}/api/v1/narrative/refine`;
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        direction,
        current_text: currentText,
      }),
    });
    if (!response.ok) {
      throw new Error(
        `Refinement failed (${response.status}): ${response.statusText || 'Unknown error'}`
      );
    }
    return response.json();
  }

  /**
   * Generate a PDF from narrative/report content.
   */
  async generatePdf(
    sessionId: string,
    content?: string,
    title?: string
  ): Promise<NarrativePdfResult> {
    const url = `${API_BASE}/api/v1/narrative/pdf`;
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        content,
        title,
      }),
    });
    if (!response.ok) {
      throw new Error(
        `PDF generation failed (${response.status}): ${response.statusText || 'Unknown error'}`
      );
    }
    return response.json();
  }

  /**
   * Check trends for brand safety using Gemini 3 Flash.
   */
  async checkTrendSafety(
    trends: Array<{ title: string; source?: string; description?: string }>,
    brand = '',
    targetAudience = '',
    safetyLevel: 'standard' | 'strict' = 'standard'
  ): Promise<TrendSafetyCheckResponse> {
    const url = `${API_BASE}/api/v1/trends/safety-check`;
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        trends,
        brand,
        target_audience: targetAudience,
        safety_level: safetyLevel,
      }),
    });
    if (!response.ok) {
      throw new Error(
        `Safety check failed (${response.status}): ${response.statusText || 'Unknown error'}`
      );
    }
    return response.json();
  }

  /**
   * List available evaluation sets.
   */
  async listEvalSets(): Promise<{eval_sets: Array<{name: string, path: string, num_cases: number}>}> {
    const url = `${API_BASE}/api/v1/eval/sets`;
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(
        `List eval sets failed (${response.status}): ${response.statusText || 'Unknown error'}`
      );
    }
    return response.json();
  }

  /**
   * Run an evaluation with an optional rubric.
   */
  async runEval(evalSetPath: string, rubricId?: string): Promise<{eval_id: string, status: string}> {
    const url = `${API_BASE}/api/v1/eval/run`;
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        eval_set_path: evalSetPath,
        rubric_id: rubricId,
      }),
    });
    if (!response.ok) {
      throw new Error(
        `Run eval failed (${response.status}): ${response.statusText || 'Unknown error'}`
      );
    }
    return response.json();
  }

  /**
   * Get evaluation results by eval ID.
   */
  async getEvalResults(evalId: string): Promise<{eval_id: string, status: string, results: any}> {
    const url = `${API_BASE}/api/v1/eval/results/${evalId}`;
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(
        `Get eval results failed (${response.status}): ${response.statusText || 'Unknown error'}`
      );
    }
    return response.json();
  }
}

export const api = new ApiClient();
