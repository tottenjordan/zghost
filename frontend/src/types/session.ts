import type { SearchTrend, YTTrend } from './trends';

export interface SessionState {
  brand?: string;
  target_product?: string;
  target_audience?: string;
  key_selling_points?: string;
  target_search_trends?: { target_search_trends: SearchTrend[] };
  target_yt_trends?: { target_yt_trends: YTTrend[] };
  img_artifact_keys?: { img_artifact_keys: string[] };
  vid_artifact_keys?: { vid_artifact_keys: string[] };
  commercial_artifact?: string;
  combined_final_cited_report?: string;
  sources?: Record<string, string>;
  gcs_folder?: string;
  [key: string]: any;
}

export interface SessionEvent {
  content?: {
    parts?: Array<{ text?: string }>;
    role?: string;
  };
  invocationId?: string;
  author?: string;
  actions?: {
    stateDelta?: Record<string, any>;
  };
  id?: string;
}

export interface Session {
  session_id: string;
  app_name: string;
  user_id: string;
  created_at: string;
  state: SessionState;
  events?: SessionEvent[];
}

export interface CreateSessionPayload {
  app_name: string;
  user_id: string;
}

export interface RunPayload {
  app_name: string;
  user_id: string;
  session_id: string;
  message: string;
  stream?: boolean;
}
