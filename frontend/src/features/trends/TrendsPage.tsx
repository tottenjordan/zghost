import { useState, useCallback, useEffect, useRef } from 'react';
import { Mic, RefreshCw, Loader2 } from 'lucide-react';
import { useSession } from '../../hooks/useSession';
import { useTrends } from './useTrends';
import { CampaignConfig } from './CampaignConfig';
import { TrendSelector } from './TrendSelector';
import { AutoTrendSelector } from './AutoTrendSelector';
import { TrendCompare } from './TrendCompare';
import { VoiceBriefAssistant } from '../voice/VoiceBriefAssistant';
import { Button } from '../../components/ui/Button';
import { api } from '../../services/api';
import { parseTrendsFromRunResponse } from '../../utils/parseTrends';
import type { CampaignConfigData } from './CampaignConfig';
import type { SearchTrend, YTTrend } from '../../types/trends';

const APP_NAME = import.meta.env.VITE_APP_NAME || 'trends_and_insights_agent';
const USER_ID = 'frontend-user';

export function TrendsPage() {
  const { session, createSession, loadSession } = useSession();
  const [fetchingTrends, setFetchingTrends] = useState(false);
  const [trendError, setTrendError] = useState<string | null>(null);
  const initRef = useRef(false);
  const {
    selectedSearchTrends,
    selectedYtTrends,
    toggleSearchTrend,
    toggleYtTrend,
    autoSelectTrends,
    autoSelecting,
    clearSelections,
  } = useTrends(session);

  const [showAutoSelect, setShowAutoSelect] = useState(false);
  const [showCompare, setShowCompare] = useState(false);
  const [showVoiceAssistant, setShowVoiceAssistant] = useState(false);
  const [configSaved, setConfigSaved] = useState(false);

  // Store parsed trends in local state
  const [availableSearchTrends, setAvailableSearchTrends] = useState<SearchTrend[]>([]);
  const [availableYtTrends, setAvailableYtTrends] = useState<YTTrend[]>([]);

  const handleSaveConfig = useCallback((_config: CampaignConfigData) => {
    setConfigSaved(true);
    setTimeout(() => setConfigSaved(false), 3000);
  }, []);

  // Fetch live trends from the ADK backend
  const handleFetchTrends = useCallback(async () => {
    setFetchingTrends(true);
    setTrendError(null);
    try {
      // Create a session if we don't have one
      let currentSession = session;
      if (!currentSession) {
        currentSession = await createSession(USER_ID);
      }

      // Send "hello" to initialize the agent, then ask for trends
      await api.sendMessage({
        app_name: APP_NAME,
        user_id: USER_ID,
        session_id: currentSession.session_id,
        message: 'hello',
      });

      // Ask for Google Search trends and parse response
      const googleResponse = await api.sendMessage({
        app_name: APP_NAME,
        user_id: USER_ID,
        session_id: currentSession.session_id,
        message: 'select a google trend',
      });

      // Ask for YouTube trends and parse response
      const ytResponse = await api.sendMessage({
        app_name: APP_NAME,
        user_id: USER_ID,
        session_id: currentSession.session_id,
        message: 'select a yt trend',
      });

      // Parse trends from both responses
      const googleParsed = parseTrendsFromRunResponse(googleResponse);
      const ytParsed = parseTrendsFromRunResponse(ytResponse);

      // Update local state with parsed trends
      if (googleParsed.searchTrends.length > 0) {
        setAvailableSearchTrends(googleParsed.searchTrends);
      }
      if (ytParsed.ytTrends.length > 0) {
        setAvailableYtTrends(ytParsed.ytTrends);
      }

      // Reload the session to get updated state
      await loadSession(USER_ID, currentSession.session_id);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to fetch trends';
      setTrendError(msg);
    } finally {
      setFetchingTrends(false);
    }
  }, [session, createSession, loadSession]);

  const handleAutoSelect = async (config: {
    num_search_trends: number;
    num_yt_trends: number;
    strategy?: 'top' | 'diverse' | 'relevance';
  }) => {
    try {
      await autoSelectTrends(config);
      // Auto-select completed, results would be in session state
    } catch (error) {
      console.error('Auto-select failed:', error);
    }
  };

  const handleConfirmSelection = () => {
    // TODO: Save selections to session state
    console.log('Confirming selections:', {
      search: selectedSearchTrends,
      yt: selectedYtTrends,
    });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="mb-2 text-3xl font-bold">Trend Discovery</h1>
          <p className="text-zinc-400">
            Configure your campaign and select trending topics to target
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            onClick={handleFetchTrends}
            disabled={fetchingTrends}
            variant="primary"
            className="flex items-center gap-2"
          >
            {fetchingTrends ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
            {fetchingTrends ? 'Fetching...' : 'Fetch Live Trends'}
          </Button>
          <Button
            onClick={() => setShowVoiceAssistant(true)}
            variant="secondary"
            className="flex items-center gap-2"
          >
            <Mic className="h-4 w-4" />
            Voice Brief
          </Button>
        </div>
      </div>

      {trendError && (
        <div className="rounded-lg border border-amber-800 bg-amber-950/50 px-4 py-2 text-sm text-amber-400">
          Could not fetch live trends: {trendError}. Showing demo data instead.
        </div>
      )}

      {/* Two-column layout */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Left column: Campaign config */}
        <div className="space-y-6">
          <CampaignConfig session={session} onSave={handleSaveConfig} />

          {configSaved && (
            <div className="rounded-lg border border-green-800 bg-green-950/50 px-4 py-2 text-sm text-green-400">
              Configuration saved successfully
            </div>
          )}

          {/* Toggle buttons for additional features */}
          <div className="flex gap-2">
            <button
              onClick={() => setShowAutoSelect(!showAutoSelect)}
              className="flex-1 rounded-lg border border-zinc-800 bg-zinc-900 px-4 py-2 text-sm font-medium transition-colors hover:bg-zinc-800"
            >
              {showAutoSelect ? 'Hide' : 'Show'} AI Auto-Select
            </button>
            <button
              onClick={() => setShowCompare(!showCompare)}
              className="flex-1 rounded-lg border border-zinc-800 bg-zinc-900 px-4 py-2 text-sm font-medium transition-colors hover:bg-zinc-800"
            >
              {showCompare ? 'Hide' : 'Show'} Compare
            </button>
          </div>

          {/* Auto-select panel */}
          {showAutoSelect && (
            <AutoTrendSelector
              loading={autoSelecting}
              onAutoSelect={handleAutoSelect}
              onAccept={() => {
                // TODO: Accept auto-selected trends
                setShowAutoSelect(false);
              }}
              onReject={() => {
                // TODO: Clear auto-selections
                setShowAutoSelect(false);
              }}
            />
          )}
        </div>

        {/* Right column: Trend selection */}
        <div className="space-y-6">
          <TrendSelector
            session={session}
            availableSearchTrends={availableSearchTrends}
            availableYtTrends={availableYtTrends}
            selectedSearchTrends={selectedSearchTrends}
            selectedYtTrends={selectedYtTrends}
            onToggleSearchTrend={toggleSearchTrend}
            onToggleYtTrend={toggleYtTrend}
            onConfirm={handleConfirmSelection}
          />

          {/* Comparison panel */}
          {showCompare && (
            <TrendCompare
              availableSearchTrends={selectedSearchTrends}
              availableYtTrends={selectedYtTrends}
            />
          )}
        </div>
      </div>

      {/* Clear selections button at bottom */}
      {(selectedSearchTrends.length > 0 || selectedYtTrends.length > 0) && (
        <div className="flex justify-center">
          <button
            onClick={clearSelections}
            className="text-sm text-zinc-500 hover:text-zinc-400"
          >
            Clear all selections
          </button>
        </div>
      )}

      {/* Voice Brief Assistant - Floating widget */}
      {showVoiceAssistant && (
        <VoiceBriefAssistant
          isFloating
          onClose={() => setShowVoiceAssistant(false)}
        />
      )}
    </div>
  );
}
