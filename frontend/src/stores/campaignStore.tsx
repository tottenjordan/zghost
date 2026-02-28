import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from 'react';
import type { SearchTrend, YTTrend } from '../types/trends';
import type { ExtendedRubric } from '../features/rating/rubric-templates';

const STORAGE_KEY = 'campaign-store';

export interface CampaignConfig {
  brand: string;
  target_product: string;
  target_audience: string;
  key_selling_points: string;
}

export interface PipelineSession {
  id: string;
  sessionId: string;
  label: string;
  status: 'running' | 'completed' | 'error' | 'idle';
  startedAt: number;
  completedAt?: number;
  config?: CampaignConfig;
  commercialDuration?: 10 | 15 | 30;
  searchTrends?: SearchTrend[];
  ytTrends?: YTTrend[];
}

export interface CampaignStoreState {
  config: CampaignConfig;
  selectedSearchTrends: SearchTrend[];
  selectedYtTrends: YTTrend[];
  activeRubrics: ExtendedRubric[];
  sessions: PipelineSession[];
  activeSessionIndex: number;
  commercialDuration: 10 | 15 | 30;
  autoStart: boolean;
  autopilot: boolean;
  // Backward compatibility - derived from active session
  sessionId: string | null;
  pipelineStatus: 'idle' | 'running' | 'completed' | 'error';
}

interface CampaignStoreActions {
  setCampaignConfig: (config: CampaignConfig) => void;
  setSelectedTrends: (search: SearchTrend[], yt: YTTrend[]) => void;
  toggleActiveRubric: (rubric: ExtendedRubric) => void;
  setAutoStart: (autoStart: boolean) => void;
  setAutopilot: (autopilot: boolean) => void;
  setSessionId: (id: string | null) => void;
  setPipelineStatus: (status: CampaignStoreState['pipelineStatus']) => void;
  addSession: (session: PipelineSession) => void;
  removeSession: (sessionId: string) => void;
  setActiveSession: (index: number) => void;
  updateSessionStatus: (sessionId: string, status: PipelineSession['status']) => void;
  setCommercialDuration: (duration: 10 | 15 | 30) => void;
  reset: () => void;
  isReadyToLaunch: () => { ready: boolean; missing: string[] };
}

type CampaignStoreContextType = CampaignStoreState & CampaignStoreActions;

const DEFAULT_STATE: CampaignStoreState = {
  config: { brand: '', target_product: '', target_audience: '', key_selling_points: '' },
  selectedSearchTrends: [],
  selectedYtTrends: [],
  activeRubrics: [],
  sessions: [],
  activeSessionIndex: -1,
  commercialDuration: 30,
  autoStart: false,
  autopilot: false,
  sessionId: null,
  pipelineStatus: 'idle',
};

const CampaignStoreContext = createContext<CampaignStoreContextType | null>(null);

function loadFromStorage(): CampaignStoreState {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      // Ensure sessions array exists
      const sessions = parsed.sessions || [];
      const activeSessionIndex = parsed.activeSessionIndex ?? -1;

      // Derive backward compat fields from active session
      const activeSession = activeSessionIndex >= 0 ? sessions[activeSessionIndex] : null;

      // Migrate activeRubric → activeRubrics for backward compat
      let activeRubrics = parsed.activeRubrics || [];
      if (!activeRubrics.length && parsed.activeRubric) {
        activeRubrics = [parsed.activeRubric];
      }

      return {
        ...DEFAULT_STATE,
        ...parsed,
        sessions,
        activeSessionIndex,
        activeRubrics,
        sessionId: activeSession?.sessionId || null,
        pipelineStatus: activeSession?.status || 'idle'
      };
    }
  } catch {
    // ignore corrupt storage
  }
  return DEFAULT_STATE;
}

function saveToStorage(state: CampaignStoreState) {
  try {
    // Don't persist transient backward-compat fields
    const { pipelineStatus: _, sessionId: __, ...persistable } = state;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(persistable));
  } catch {
    // storage full or unavailable
  }
}

export function CampaignStoreProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<CampaignStoreState>(loadFromStorage);

  // Persist on every state change
  useEffect(() => {
    saveToStorage(state);
  }, [state]);

  const setCampaignConfig = useCallback((config: CampaignConfig) => {
    setState((prev) => ({ ...prev, config }));
  }, []);

  const setSelectedTrends = useCallback((search: SearchTrend[], yt: YTTrend[]) => {
    setState((prev) => ({ ...prev, selectedSearchTrends: search, selectedYtTrends: yt }));
  }, []);

  const toggleActiveRubric = useCallback((rubric: ExtendedRubric) => {
    setState((prev) => {
      const exists = prev.activeRubrics.some(r => r.id === rubric.id);
      return {
        ...prev,
        activeRubrics: exists
          ? prev.activeRubrics.filter(r => r.id !== rubric.id)
          : [...prev.activeRubrics, rubric],
      };
    });
  }, []);

  const setAutoStart = useCallback((autoStart: boolean) => {
    setState((prev) => ({ ...prev, autoStart }));
  }, []);

  const setAutopilot = useCallback((autopilot: boolean) => {
    setState((prev) => ({ ...prev, autopilot }));
  }, []);

  const setSessionId = useCallback((id: string | null) => {
    setState((prev) => {
      // Update active session's sessionId
      if (prev.activeSessionIndex >= 0 && prev.sessions.length > prev.activeSessionIndex) {
        const updatedSessions = [...prev.sessions];
        updatedSessions[prev.activeSessionIndex] = {
          ...updatedSessions[prev.activeSessionIndex],
          sessionId: id || '',
        };
        return { ...prev, sessions: updatedSessions, sessionId: id };
      }
      return { ...prev, sessionId: id };
    });
  }, []);

  const setPipelineStatus = useCallback((status: CampaignStoreState['pipelineStatus']) => {
    setState((prev) => {
      // Update active session's status
      if (prev.activeSessionIndex >= 0 && prev.sessions.length > prev.activeSessionIndex) {
        const updatedSessions = [...prev.sessions];
        updatedSessions[prev.activeSessionIndex] = {
          ...updatedSessions[prev.activeSessionIndex],
          status,
          completedAt: status === 'completed' || status === 'error' ? Date.now() : undefined,
        };
        return { ...prev, sessions: updatedSessions, pipelineStatus: status };
      }
      return { ...prev, pipelineStatus: status };
    });
  }, []);

  const addSession = useCallback((session: PipelineSession) => {
    setState((prev) => {
      const sessions = [...prev.sessions, session];
      const activeSessionIndex = sessions.length - 1;
      return {
        ...prev,
        sessions,
        activeSessionIndex,
        sessionId: session.sessionId,
        pipelineStatus: session.status,
      };
    });
  }, []);

  const removeSession = useCallback((sessionId: string) => {
    setState((prev) => {
      const sessionIndex = prev.sessions.findIndex((s) => s.sessionId === sessionId);
      if (sessionIndex === -1) return prev;

      const sessions = prev.sessions.filter((s) => s.sessionId !== sessionId);
      let activeSessionIndex = prev.activeSessionIndex;

      // Adjust active index if needed
      if (activeSessionIndex === sessionIndex) {
        activeSessionIndex = sessions.length > 0 ? Math.max(0, sessionIndex - 1) : -1;
      } else if (activeSessionIndex > sessionIndex) {
        activeSessionIndex--;
      }

      const activeSession = activeSessionIndex >= 0 ? sessions[activeSessionIndex] : null;

      return {
        ...prev,
        sessions,
        activeSessionIndex,
        sessionId: activeSession?.sessionId || null,
        pipelineStatus: activeSession?.status || 'idle',
      };
    });
  }, []);

  const setActiveSession = useCallback((index: number) => {
    setState((prev) => {
      if (index < 0 || index >= prev.sessions.length) return prev;
      const activeSession = prev.sessions[index];
      return {
        ...prev,
        activeSessionIndex: index,
        sessionId: activeSession.sessionId,
        pipelineStatus: activeSession.status,
      };
    });
  }, []);

  const updateSessionStatus = useCallback((sessionId: string, status: PipelineSession['status']) => {
    setState((prev) => {
      const sessionIndex = prev.sessions.findIndex((s) => s.sessionId === sessionId);
      if (sessionIndex === -1) return prev;

      const updatedSessions = [...prev.sessions];
      updatedSessions[sessionIndex] = {
        ...updatedSessions[sessionIndex],
        status,
        completedAt: status === 'completed' || status === 'error' ? Date.now() : undefined,
      };

      // Update backward compat fields if this is active session
      const isActive = prev.activeSessionIndex === sessionIndex;

      return {
        ...prev,
        sessions: updatedSessions,
        ...(isActive && { pipelineStatus: status }),
      };
    });
  }, []);

  const setCommercialDuration = useCallback((duration: 10 | 15 | 30) => {
    setState((prev) => ({ ...prev, commercialDuration: duration }));
  }, []);

  const reset = useCallback(() => {
    setState(DEFAULT_STATE);
    localStorage.removeItem(STORAGE_KEY);
  }, []);

  const isReadyToLaunch = useCallback(() => {
    const missing: string[] = [];
    if (!state.config.brand && !state.config.target_product) {
      missing.push('Brand or Product');
    }
    if (state.selectedSearchTrends.length === 0 && state.selectedYtTrends.length === 0) {
      missing.push('At least 1 trend');
    }
    return { ready: missing.length === 0, missing };
  }, [state.config, state.selectedSearchTrends, state.selectedYtTrends]);

  const value: CampaignStoreContextType = {
    ...state,
    setCampaignConfig,
    setSelectedTrends,
    toggleActiveRubric,
    setAutoStart,
    setAutopilot,
    setSessionId,
    setPipelineStatus,
    addSession,
    removeSession,
    setActiveSession,
    updateSessionStatus,
    setCommercialDuration,
    reset,
    isReadyToLaunch,
  };

  return (
    <CampaignStoreContext.Provider value={value}>
      {children}
    </CampaignStoreContext.Provider>
  );
}

export function useCampaignStore(): CampaignStoreContextType {
  const ctx = useContext(CampaignStoreContext);
  if (!ctx) {
    throw new Error('useCampaignStore must be used within CampaignStoreProvider');
  }
  return ctx;
}
