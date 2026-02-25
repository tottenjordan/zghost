import { useState, useCallback, useEffect, useRef } from 'react';
import { Mic, RefreshCw, Loader2 } from 'lucide-react';
import { useSession } from '../../hooks/useSession';
import { useTrends } from './useTrends';
import { useCampaignStore } from '../../stores/campaignStore';
import { CampaignConfig } from './CampaignConfig';
import { TrendSelector } from './TrendSelector';
import { AutoTrendSelector } from './AutoTrendSelector';
import { TrendCompare } from './TrendCompare';
import { VoiceBriefAssistant } from '../voice/VoiceBriefAssistant';
import { Button } from '../../components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../components/ui/Tabs';
import { fetchLiveTrends, getCachedTrends, autoSelectFromAvailable } from '../../services/trendsCache';
import type { CampaignConfigData } from './CampaignConfig';
import type { SearchTrend, YTTrend } from '../../types/trends';

export function TrendsPage() {
  const { session, createSession, loadSession } = useSession();
  const {
    config: storeConfig,
    selectedSearchTrends,
    selectedYtTrends,
    setCampaignConfig: setStoreConfig,
    setSelectedTrends
  } = useCampaignStore();

  const [fetchingTrends, setFetchingTrends] = useState(false);
  const [trendError, setTrendError] = useState<string | null>(null);
  const initRef = useRef(false);
  const {
    toggleSearchTrend,
    toggleYtTrend,
    clearSelections,
  } = useTrends({
    selectedSearchTrends,
    selectedYtTrends,
    setSelectedTrends,
  });

  const [showAutoSelect, setShowAutoSelect] = useState(false);
  const [showCompare, setShowCompare] = useState(false);
  const [showVoiceAssistant, setShowVoiceAssistant] = useState(false);
  const [configSaved, setConfigSaved] = useState(false);

  // Store parsed trends in local state
  const [availableSearchTrends, setAvailableSearchTrends] = useState<SearchTrend[]>([]);
  const [availableYtTrends, setAvailableYtTrends] = useState<YTTrend[]>([]);

  // Auto-select results (staging area before user accepts)
  const [autoSelectedSearchTrends, setAutoSelectedSearchTrends] = useState<SearchTrend[]>([]);
  const [autoSelectedYtTrends, setAutoSelectedYtTrends] = useState<YTTrend[]>([]);
  const [aiReasoning, setAiReasoning] = useState<string>('');
  const [autoSelectLoading, setAutoSelectLoading] = useState(false);

  const handleSaveConfig = useCallback((config: CampaignConfigData) => {
    setStoreConfig(config);
    setConfigSaved(true);
    setTimeout(() => setConfigSaved(false), 3000);
  }, [setStoreConfig]);

  // Core trend fetch logic (used by auto-fetch and manual refresh)
  const doFetchTrends = useCallback(async (force = false) => {
    setFetchingTrends(true);
    setTrendError(null);
    try {
      const result = await fetchLiveTrends(force);

      if (result.searchTrends.length > 0) {
        setAvailableSearchTrends(result.searchTrends);
      }
      if (result.ytTrends.length > 0) {
        setAvailableYtTrends(result.ytTrends);
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to fetch trends';
      setTrendError(msg);
    } finally {
      setFetchingTrends(false);
    }
  }, []);

  // Auto-fetch on page load (uses cache if available)
  useEffect(() => {
    if (initRef.current) return;
    initRef.current = true;

    // Check cache first — instant if valid
    const cached = getCachedTrends();
    if (cached) {
      if (cached.searchTrends.length > 0) setAvailableSearchTrends(cached.searchTrends);
      if (cached.ytTrends.length > 0) setAvailableYtTrends(cached.ytTrends);
      return;
    }

    // Otherwise fetch from backend
    doFetchTrends();
  }, [doFetchTrends]);

  // Manual refresh (force bypasses cache)
  const handleFetchTrends = useCallback(() => {
    doFetchTrends(true);
  }, [doFetchTrends]);

  // Auto-select — works locally against available trends (no backend call)
  const handleAutoSelect = async (config: {
    num_search_trends: number;
    num_yt_trends: number;
    strategy?: 'top' | 'diverse' | 'relevance';
  }) => {
    if (availableSearchTrends.length === 0 && availableYtTrends.length === 0) {
      setTrendError('No trends available yet. Wait for trends to load first.');
      return;
    }

    setAutoSelectLoading(true);
    try {
      const available = {
        searchTrends: availableSearchTrends,
        ytTrends: availableYtTrends,
        fetchedAt: Date.now(),
        sessionId: '',
      };

      const result = autoSelectFromAvailable(available, {
        num_search_trends: config.num_search_trends,
        num_yt_trends: config.num_yt_trends,
        strategy: config.strategy || 'relevance',
        campaign: storeConfig,
      });

      setAutoSelectedSearchTrends(result.searchTrends);
      setAutoSelectedYtTrends(result.ytTrends);
      setAiReasoning(result.reasoning);
    } finally {
      setAutoSelectLoading(false);
    }
  };

  // Accept auto-selected trends — move them into the main selection
  const handleAcceptAutoSelect = () => {
    setSelectedTrends(autoSelectedSearchTrends, autoSelectedYtTrends); // Persist to store
    // Clear auto-select results and close panel
    setAutoSelectedSearchTrends([]);
    setAutoSelectedYtTrends([]);
    setAiReasoning('');
    setShowAutoSelect(false);
  };

  // Reject auto-selection — clear results, keep panel open for retry
  const handleRejectAutoSelect = () => {
    setAutoSelectedSearchTrends([]);
    setAutoSelectedYtTrends([]);
    setAiReasoning('');
  };

  const trendsLoaded = availableSearchTrends.length > 0 || availableYtTrends.length > 0;
  const totalSelected = selectedSearchTrends.length + selectedYtTrends.length;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="mb-2 text-3xl font-bold">Trend Discovery</h1>
          <p className="text-zinc-400">
            Configure your campaign and select trending topics to target
          </p>
          {trendsLoaded && (
            <p className="mt-1 text-xs text-zinc-500">
              {availableSearchTrends.length} Google + {availableYtTrends.length} YouTube trends loaded
            </p>
          )}
        </div>
      </div>

      {trendError && (
        <div className="rounded-lg border border-amber-800 bg-amber-950/50 px-4 py-2 text-sm text-amber-400">
          Could not fetch live trends: {trendError}. Showing demo data instead.
        </div>
      )}

      {fetchingTrends && !trendsLoaded && (
        <div className="flex items-center gap-3 rounded-lg border border-blue-800 bg-blue-950/30 px-4 py-3 text-sm text-blue-400">
          <Loader2 className="h-4 w-4 animate-spin" />
          Fetching live trends from backend agents... This may take a moment.
        </div>
      )}

      {/* Horizontal tabs layout */}
      <Tabs defaultValue="campaign">
        <TabsList>
          <TabsTrigger value="campaign">Campaign</TabsTrigger>
          <TabsTrigger value="trends">
            Trends {totalSelected > 0 && `(${totalSelected})`}
          </TabsTrigger>
          <TabsTrigger value="review">Review</TabsTrigger>
        </TabsList>

        {/* Tab 1: Campaign Config */}
        <TabsContent value="campaign">
          <div className="space-y-6">
            <CampaignConfig session={session} onSave={handleSaveConfig} />

            {configSaved && (
              <div className="rounded-lg border border-green-800 bg-green-950/50 px-4 py-2 text-sm text-green-400">
                Configuration saved successfully
              </div>
            )}
          </div>
        </TabsContent>

        {/* Tab 2: Trends */}
        <TabsContent value="trends">
          <div className="space-y-6">
            {/* Fetch and Voice buttons at the top of Trends tab */}
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
                {fetchingTrends ? 'Fetching...' : 'Refresh Trends'}
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
                loading={autoSelectLoading}
                onAutoSelect={handleAutoSelect}
                autoSelectedSearchTrends={autoSelectedSearchTrends}
                autoSelectedYtTrends={autoSelectedYtTrends}
                aiReasoning={aiReasoning}
                onAccept={handleAcceptAutoSelect}
                onReject={handleRejectAutoSelect}
              />
            )}

            {/* Trend selector */}
            <TrendSelector
              availableSearchTrends={availableSearchTrends}
              availableYtTrends={availableYtTrends}
              selectedSearchTrends={selectedSearchTrends}
              selectedYtTrends={selectedYtTrends}
              onToggleSearchTrend={toggleSearchTrend}
              onToggleYtTrend={toggleYtTrend}
            />

            {/* Comparison panel */}
            {showCompare && (
              <TrendCompare
                availableSearchTrends={selectedSearchTrends}
                availableYtTrends={selectedYtTrends}
              />
            )}

            {/* Clear selections button at bottom */}
            {totalSelected > 0 && (
              <div className="flex justify-center">
                <button
                  onClick={clearSelections}
                  className="text-sm text-zinc-500 hover:text-zinc-400"
                >
                  Clear all selections
                </button>
              </div>
            )}
          </div>
        </TabsContent>

        {/* Tab 3: Review */}
        <TabsContent value="review">
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Campaign Summary</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="grid gap-4 md:grid-cols-2">
                    <div>
                      <p className="text-sm font-medium text-zinc-400">Brand</p>
                      <p className="mt-1 text-zinc-100">
                        {storeConfig?.brand || 'Not set'}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-zinc-400">Target Product</p>
                      <p className="mt-1 text-zinc-100">
                        {storeConfig?.target_product || 'Not set'}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-zinc-400">Target Audience</p>
                      <p className="mt-1 text-zinc-100">
                        {storeConfig?.target_audience || 'Not set'}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-zinc-400">Key Selling Points</p>
                      <p className="mt-1 text-zinc-100">
                        {storeConfig?.key_selling_points || 'Not set'}
                      </p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Selected Trends</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <p className="text-sm font-medium text-zinc-400">
                      Google Search Trends ({selectedSearchTrends.length})
                    </p>
                    {selectedSearchTrends.length > 0 ? (
                      <ul className="mt-2 space-y-1">
                        {selectedSearchTrends.map((trend) => (
                          <li key={trend.rank} className="text-sm text-zinc-100">
                            • {trend.title}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="mt-2 text-sm text-zinc-500">No trends selected</p>
                    )}
                  </div>
                  <div>
                    <p className="text-sm font-medium text-zinc-400">
                      YouTube Trends ({selectedYtTrends.length})
                    </p>
                    {selectedYtTrends.length > 0 ? (
                      <ul className="mt-2 space-y-1">
                        {selectedYtTrends.map((trend) => (
                          <li key={trend.rank} className="text-sm text-zinc-100">
                            • {trend.title}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="mt-2 text-sm text-zinc-500">No trends selected</p>
                    )}
                  </div>
                  <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 px-4 py-3">
                    <p className="text-sm font-medium text-zinc-300">
                      Total: {totalSelected} trend{totalSelected !== 1 ? 's' : ''} selected
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>

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
