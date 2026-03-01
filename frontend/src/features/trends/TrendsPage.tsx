import { useState, useCallback, useEffect, useRef } from 'react';
import { RefreshCw, Loader2, Star, ChevronDown, Check, ArrowRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useSession } from '../../hooks/useSession';
import { useTrends } from './useTrends';
import { useCampaignStore } from '../../stores/campaignStore';
import { CampaignConfig } from './CampaignConfig';
import { TrendSelector } from './TrendSelector';
import { AutoTrendSelector } from './AutoTrendSelector';
import { TrendCompare } from './TrendCompare';
import { Button } from '../../components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../components/ui/Tabs';
import { fetchLiveTrends, getCachedTrends, autoSelectFromAvailable } from '../../services/trendsCache';
import { RubricLibrary } from '../rating/RubricLibrary';
import { RubricEditor } from '../rating/RubricEditor';
import { DEFAULT_RUBRICS, type ExtendedRubric } from '../rating/rubric-templates';
import { cn } from '../../lib/utils';
import type { CampaignConfigData } from './CampaignConfig';
import type { SearchTrend, YTTrend } from '../../types/trends';
import type { BrandSafetyResult } from '../../services/brandSafety';

type WizardStep = 'campaign' | 'trends' | 'evaluation' | 'review';
const STEPS: { key: WizardStep; label: string; tabLabel: string; number: number }[] = [
  { key: 'campaign', label: 'Campaign Setup', tabLabel: 'Campaign', number: 1 },
  { key: 'trends', label: 'Trend Selection', tabLabel: 'Trends', number: 2 },
  { key: 'evaluation', label: 'Evaluation Rubric', tabLabel: 'Evaluation', number: 3 },
  { key: 'review', label: 'Review & Launch', tabLabel: 'Review', number: 4 },
];

export function TrendsPage() {
  const navigate = useNavigate();
  const { state: sessionState } = useSession();
  const {
    config: storeConfig,
    selectedSearchTrends,
    selectedYtTrends,
    activeRubrics,
    setCampaignConfig: setStoreConfig,
    setSelectedTrends,
    toggleActiveRubric,
    setAutoStart,
    isReadyToLaunch,
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
  const [configSaved, setConfigSaved] = useState(false);
  const [activeStep, setActiveStep] = useState<WizardStep>('campaign');

  // Rubric editor state
  const [editingRubric, setEditingRubric] = useState<ExtendedRubric | null>(null);
  const [isCreatingRubric, setIsCreatingRubric] = useState(false);

  // Load available rubrics from localStorage
  const [availableRubrics, setAvailableRubrics] = useState<ExtendedRubric[]>([]);
  useEffect(() => {
    const stored = localStorage.getItem('rating-rubrics');
    if (stored) {
      setAvailableRubrics(JSON.parse(stored));
    } else {
      setAvailableRubrics(DEFAULT_RUBRICS);
    }
  }, []);

  const saveRubricsToStorage = (rubrics: ExtendedRubric[]) => {
    setAvailableRubrics(rubrics);
    localStorage.setItem('rating-rubrics', JSON.stringify(rubrics));
  };

  // Store parsed trends in local state
  const [availableSearchTrends, setAvailableSearchTrends] = useState<SearchTrend[]>([]);
  const [availableYtTrends, setAvailableYtTrends] = useState<YTTrend[]>([]);

  // Auto-select results
  const [autoSelectedSearchTrends, setAutoSelectedSearchTrends] = useState<SearchTrend[]>([]);
  const [autoSelectedYtTrends, setAutoSelectedYtTrends] = useState<YTTrend[]>([]);
  const [aiReasoning, setAiReasoning] = useState<string>('');
  const [safetyResult, setSafetyResult] = useState<BrandSafetyResult | undefined>(undefined);
  const [autoSelectLoading, setAutoSelectLoading] = useState(false);

  const handleSaveConfig = useCallback((config: CampaignConfigData) => {
    setStoreConfig(config);
    setConfigSaved(true);
    setTimeout(() => setConfigSaved(false), 3000);
  }, [setStoreConfig]);

  // Core trend fetch logic
  const doFetchTrends = useCallback(async (force = false) => {
    setFetchingTrends(true);
    setTrendError(null);
    try {
      const result = await fetchLiveTrends(force);
      if (result.searchTrends.length > 0) setAvailableSearchTrends(result.searchTrends);
      if (result.ytTrends.length > 0) setAvailableYtTrends(result.ytTrends);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to fetch trends';
      setTrendError(msg);
    } finally {
      setFetchingTrends(false);
    }
  }, []);

  // Auto-fetch on page load
  useEffect(() => {
    if (initRef.current) return;
    initRef.current = true;
    const cached = getCachedTrends();
    if (cached) {
      if (cached.searchTrends.length > 0) setAvailableSearchTrends(cached.searchTrends);
      if (cached.ytTrends.length > 0) setAvailableYtTrends(cached.ytTrends);
      return;
    }
    doFetchTrends();
  }, [doFetchTrends]);

  // Voice action listener for trend selection
  useEffect(() => {
    const handler = (e: Event) => {
      const { action, params } = (e as CustomEvent).detail;
      if (action === 'select_google_trend') {
        const rank = params?.rank;
        const trend = availableSearchTrends.find(t => t.rank === rank);
        if (trend) toggleSearchTrend(trend);
      } else if (action === 'select_youtube_trend') {
        const rank = params?.rank;
        const trend = availableYtTrends.find(t => t.rank === rank);
        if (trend) toggleYtTrend(trend);
      }
    };
    window.addEventListener('voice-action', handler);
    return () => window.removeEventListener('voice-action', handler);
  }, [availableSearchTrends, availableYtTrends, toggleSearchTrend, toggleYtTrend]);

  const handleFetchTrends = useCallback(() => {
    doFetchTrends(true);
  }, [doFetchTrends]);

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
      setSafetyResult(result.safetyResult);
    } finally {
      setAutoSelectLoading(false);
    }
  };

  const handleAcceptAutoSelect = () => {
    setSelectedTrends(autoSelectedSearchTrends, autoSelectedYtTrends);
    setAutoSelectedSearchTrends([]);
    setAutoSelectedYtTrends([]);
    setAiReasoning('');
    setSafetyResult(undefined);
    setShowAutoSelect(false);
  };

  const handleRejectAutoSelect = () => {
    setAutoSelectedSearchTrends([]);
    setAutoSelectedYtTrends([]);
    setAiReasoning('');
    setSafetyResult(undefined);
  };

  // Rubric management handlers
  const handleCreateRubric = () => {
    setEditingRubric(null);
    setIsCreatingRubric(true);
  };

  const handleEditRubric = (rubric: ExtendedRubric) => {
    setEditingRubric(rubric);
    setIsCreatingRubric(true);
  };

  const handleSaveRubric = (rubricData: Omit<ExtendedRubric, 'id'>) => {
    if (editingRubric) {
      const updated = availableRubrics.map(r =>
        r.id === editingRubric.id ? { ...rubricData, id: editingRubric.id } : r
      );
      saveRubricsToStorage(updated);
    } else {
      const newRubric: ExtendedRubric = {
        ...rubricData,
        id: `rubric-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
      };
      saveRubricsToStorage([...availableRubrics, newRubric]);
    }
    setIsCreatingRubric(false);
    setEditingRubric(null);
  };

  const handleCloneRubric = (id: string) => {
    const source = availableRubrics.find(r => r.id === id);
    if (!source) return;
    const clone: ExtendedRubric = {
      ...source,
      id: `rubric-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
      name: `${source.name} (Copy)`,
    };
    saveRubricsToStorage([...availableRubrics, clone]);
  };

  const handleDeleteRubric = (id: string) => {
    saveRubricsToStorage(availableRubrics.filter(r => r.id !== id));
    const rubricToRemove = activeRubrics.find(r => r.id === id);
    if (rubricToRemove) toggleActiveRubric(rubricToRemove);
  };

  const handleCreateFromTemplate = (template: ExtendedRubric) => {
    const newRubric: ExtendedRubric = {
      ...template,
      id: `rubric-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
    };
    saveRubricsToStorage([...availableRubrics, newRubric]);
  };

  // Step completion checks
  const isCampaignComplete = !!(storeConfig?.brand || storeConfig?.target_product);
  const totalSelected = selectedSearchTrends.length + selectedYtTrends.length;
  const isTrendsComplete = totalSelected > 0;
  const isEvaluationComplete = activeRubrics.length > 0;
  const { ready, missing } = isReadyToLaunch();

  const getStepStatus = (step: WizardStep): 'pending' | 'active' | 'completed' => {
    if (step === activeStep) return 'active';
    return 'pending';
  };

  const currentStepIndex = STEPS.findIndex(s => s.key === activeStep);
  const trendsLoaded = availableSearchTrends.length > 0 || availableYtTrends.length > 0;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="mb-2 text-3xl font-bold">Configure</h1>
          <p className="text-zinc-400">
            Set up your campaign, select trends, and configure evaluation
          </p>
        </div>
      </div>

      {/* Step progress bar */}
      <div className="flex items-center gap-2 text-sm text-zinc-400">
        <span className="font-medium text-zinc-300">
          Step {currentStepIndex + 1} of {STEPS.length}:
        </span>
        <span>{STEPS[currentStepIndex]?.label}</span>
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

      {/* Tabs with step indicators */}
      <Tabs defaultValue="campaign">
        <TabsList>
          {STEPS.map((step) => {
            const status = getStepStatus(step.key);
            return (
              <TabsTrigger key={step.key} value={step.key}>
                <span
                  onClick={() => setActiveStep(step.key)}
                  className="flex items-center gap-1.5"
                >
                  <span className={cn(
                    'flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold transition-all',
                    status === 'completed' && 'bg-green-600 text-white',
                    status === 'active' && 'ring-2 ring-blue-500 bg-blue-600/20 text-blue-400',
                    status === 'pending' && 'bg-zinc-700 text-zinc-400',
                  )}>
                    {status === 'completed' ? (
                      <Check className="h-3 w-3" />
                    ) : (
                      step.number
                    )}
                  </span>
                  {step.tabLabel}
                </span>
              </TabsTrigger>
            );
          })}
        </TabsList>

        {/* Step 1: Campaign Config */}
        <TabsContent value="campaign">
          <div className="space-y-6" onClick={() => setActiveStep('campaign')}>
            <CampaignConfig sessionState={sessionState} onSave={handleSaveConfig} />
            {configSaved && (
              <div className="rounded-lg border border-green-800 bg-green-950/50 px-4 py-2 text-sm text-green-400">
                Configuration saved successfully
              </div>
            )}
          </div>
        </TabsContent>

        {/* Step 2: Trends */}
        <TabsContent value="trends">
          <div className="space-y-6" onClick={() => setActiveStep('trends')}>
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
            </div>

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

            {showAutoSelect && (
              <AutoTrendSelector
                loading={autoSelectLoading}
                onAutoSelect={handleAutoSelect}
                autoSelectedSearchTrends={autoSelectedSearchTrends}
                autoSelectedYtTrends={autoSelectedYtTrends}
                aiReasoning={aiReasoning}
                safetyResult={safetyResult}
                onAccept={handleAcceptAutoSelect}
                onReject={handleRejectAutoSelect}
              />
            )}

            <TrendSelector
              availableSearchTrends={availableSearchTrends}
              availableYtTrends={availableYtTrends}
              selectedSearchTrends={selectedSearchTrends}
              selectedYtTrends={selectedYtTrends}
              onToggleSearchTrend={toggleSearchTrend}
              onToggleYtTrend={toggleYtTrend}
            />

            {showCompare && (
              <TrendCompare
                availableSearchTrends={selectedSearchTrends}
                availableYtTrends={selectedYtTrends}
              />
            )}

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

        {/* Step 3: Evaluation */}
        <TabsContent value="evaluation">
          <div className="space-y-6" onClick={() => setActiveStep('evaluation')}>
            {isCreatingRubric ? (
              <RubricEditor
                rubric={editingRubric || undefined}
                onSave={handleSaveRubric}
                onCancel={() => {
                  setIsCreatingRubric(false);
                  setEditingRubric(null);
                }}
              />
            ) : (
              <RubricLibrary
                rubrics={availableRubrics}
                onEdit={handleEditRubric}
                onClone={handleCloneRubric}
                onDelete={handleDeleteRubric}
                onCreate={handleCreateRubric}
                onCreateFromTemplate={handleCreateFromTemplate}
                activeRubricIds={activeRubrics.map(r => r.id)}
                onToggleActive={toggleActiveRubric}
              />
            )}
          </div>
        </TabsContent>

        {/* Step 4: Review */}
        <TabsContent value="review">
          <div className="space-y-6" onClick={() => setActiveStep('review')}>
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
                            &bull; {trend.title}
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
                            &bull; {trend.title}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="mt-2 text-sm text-zinc-500">No trends selected</p>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Rubric Preview */}
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2">
                    <Star className="w-4 h-4" />
                    Evaluation Rubric
                  </CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                {activeRubrics.length > 0 ? (
                  <div className="space-y-3">
                    {activeRubrics.map((rubric) => (
                      <div key={rubric.id} className="space-y-2">
                        <div className="flex items-center gap-2">
                          <span className="rounded-full bg-green-900/50 px-2.5 py-0.5 text-xs font-medium text-green-400 border border-green-700">
                            {rubric.name}
                          </span>
                          <span className="text-xs text-zinc-500">
                            {rubric.criteria.length} criteria
                          </span>
                        </div>
                        <div className="space-y-1">
                          {rubric.criteria.map((c) => (
                            <div key={c.id} className="flex items-center justify-between text-xs">
                              <span className="text-zinc-400">{c.name}</span>
                              <span className="text-zinc-500">weight: {c.weight}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-amber-400">
                    No rubric selected &mdash; pipeline will use default evaluation
                  </p>
                )}
              </CardContent>
            </Card>

            {/* Missing items warnings */}
            {!ready && missing.length > 0 && (
              <div className="space-y-1">
                {missing.map((item) => (
                  <div key={item} className="flex items-center gap-2 rounded-lg border border-amber-800/50 bg-amber-950/30 px-3 py-2 text-sm text-amber-400">
                    <span className="text-amber-500">&#9888;</span>
                    Missing: {item}
                  </div>
                ))}
              </div>
            )}

            {/* Launch button */}
            <Button
              onClick={() => { setAutoStart(true); navigate('/orchestration'); }}
              disabled={!ready}
              variant="primary"
              className="w-full py-3 text-base font-semibold flex items-center justify-center gap-2"
            >
              Add Execution Run to Orchestrator
              <ArrowRight className="h-5 w-5" />
            </Button>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
