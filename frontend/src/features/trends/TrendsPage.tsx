import { useState, useCallback } from 'react';
import { Mic } from 'lucide-react';
import { useSession } from '../../hooks/useSession';
import { useTrends } from './useTrends';
import { CampaignConfig } from './CampaignConfig';
import { TrendSelector } from './TrendSelector';
import { AutoTrendSelector } from './AutoTrendSelector';
import { TrendCompare } from './TrendCompare';
import { VoiceBriefAssistant } from '../voice/VoiceBriefAssistant';
import { Button } from '../../components/ui/Button';
import type { CampaignConfigData } from './CampaignConfig';

export function TrendsPage() {
  const { session } = useSession();
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

  const handleSaveConfig = useCallback((_config: CampaignConfigData) => {
    setConfigSaved(true);
    // Clear success indicator after 3 seconds
    setTimeout(() => setConfigSaved(false), 3000);
  }, []);

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
        <Button
          onClick={() => setShowVoiceAssistant(true)}
          variant="secondary"
          className="flex items-center gap-2"
        >
          <Mic className="h-4 w-4" />
          Voice Brief Assistant
        </Button>
      </div>

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
