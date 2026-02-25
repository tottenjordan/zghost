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

export interface CampaignStoreState {
  config: CampaignConfig;
  selectedSearchTrends: SearchTrend[];
  selectedYtTrends: YTTrend[];
  activeRubric: ExtendedRubric | null;
  sessionId: string | null;
  pipelineStatus: 'idle' | 'running' | 'completed' | 'error';
}

interface CampaignStoreActions {
  setCampaignConfig: (config: CampaignConfig) => void;
  setSelectedTrends: (search: SearchTrend[], yt: YTTrend[]) => void;
  setActiveRubric: (rubric: ExtendedRubric | null) => void;
  setSessionId: (id: string | null) => void;
  setPipelineStatus: (status: CampaignStoreState['pipelineStatus']) => void;
  reset: () => void;
  isReadyToLaunch: () => { ready: boolean; missing: string[] };
}

type CampaignStoreContextType = CampaignStoreState & CampaignStoreActions;

const DEFAULT_STATE: CampaignStoreState = {
  config: { brand: '', target_product: '', target_audience: '', key_selling_points: '' },
  selectedSearchTrends: [],
  selectedYtTrends: [],
  activeRubric: null,
  sessionId: null,
  pipelineStatus: 'idle',
};

const CampaignStoreContext = createContext<CampaignStoreContextType | null>(null);

function loadFromStorage(): CampaignStoreState {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      return { ...DEFAULT_STATE, ...parsed, pipelineStatus: 'idle' };
    }
  } catch {
    // ignore corrupt storage
  }
  return DEFAULT_STATE;
}

function saveToStorage(state: CampaignStoreState) {
  try {
    // Don't persist transient state like pipelineStatus
    const { pipelineStatus: _, ...persistable } = state;
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

  const setActiveRubric = useCallback((rubric: ExtendedRubric | null) => {
    setState((prev) => ({ ...prev, activeRubric: rubric }));
  }, []);

  const setSessionId = useCallback((id: string | null) => {
    setState((prev) => ({ ...prev, sessionId: id }));
  }, []);

  const setPipelineStatus = useCallback((status: CampaignStoreState['pipelineStatus']) => {
    setState((prev) => ({ ...prev, pipelineStatus: status }));
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
    setActiveRubric,
    setSessionId,
    setPipelineStatus,
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
