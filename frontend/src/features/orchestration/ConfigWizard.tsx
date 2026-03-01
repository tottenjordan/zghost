import { useState } from 'react';
import { Check, ChevronRight, ChevronLeft, Play } from 'lucide-react';
import { cn } from '../../lib/utils';
import type { CampaignConfig } from '../../stores/campaignStore';
import type { SearchTrend, YTTrend } from '../../types/trends';
import type { ExtendedRubric } from '../rating/rubric-templates';
import { TrendSafetyGuardrail } from '../trends/TrendSafetyGuardrail';

interface ConfigWizardProps {
  config: CampaignConfig;
  onConfigChange: (config: CampaignConfig) => void;
  selectedSearchTrends: SearchTrend[];
  selectedYtTrends: YTTrend[];
  commercialDuration: 10 | 15 | 30;
  onDurationChange: (d: 10 | 15 | 30) => void;
  autopilot: boolean;
  onAutopilotChange: (v: boolean) => void;
  isRunning: boolean;
  onLaunch: () => void;
  activeRubrics: ExtendedRubric[];
}

type Step = 1 | 2 | 3 | 4;

export function ConfigWizard({
  config,
  onConfigChange,
  selectedSearchTrends,
  selectedYtTrends,
  commercialDuration,
  onDurationChange,
  autopilot,
  onAutopilotChange,
  isRunning,
  onLaunch,
  activeRubrics,
}: ConfigWizardProps) {
  const [currentStep, setCurrentStep] = useState<Step>(1);
  const [confirmedSteps, setConfirmedSteps] = useState<Set<Step>>(new Set());

  // Step data-readiness checks (used for gating "Next" button)
  const isStep1Ready = () => config.brand.trim() !== '' || config.target_product.trim() !== '';
  const isStep2Ready = () => selectedSearchTrends.length > 0 || selectedYtTrends.length > 0;
  const isStep3Ready = () => true; // Settings always have defaults

  const canProceedToStep = (step: Step): boolean => {
    if (step === 1) return true;
    if (step === 2) return confirmedSteps.has(1);
    if (step === 3) return confirmedSteps.has(1) && confirmedSteps.has(2);
    if (step === 4) return confirmedSteps.has(1) && confirmedSteps.has(2) && confirmedSteps.has(3);
    return false;
  };

  const getStepStatus = (step: Step): 'complete' | 'current' | 'future' => {
    if (confirmedSteps.has(step)) return 'complete';
    if (step === currentStep) return 'current';
    return 'future';
  };

  const steps = [
    { number: 1 as Step, label: 'Campaign' },
    { number: 2 as Step, label: 'Trends' },
    { number: 3 as Step, label: 'Settings' },
    { number: 4 as Step, label: 'Review' },
  ];

  const handleStepClick = (step: Step) => {
    if (!isRunning && canProceedToStep(step)) {
      setCurrentStep(step);
    }
  };

  const handleNext = () => {
    // Mark the current step as confirmed before advancing
    setConfirmedSteps((prev) => new Set(prev).add(currentStep));
    if (currentStep < 4) {
      setCurrentStep((currentStep + 1) as Step);
    } else {
      onLaunch();
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep((currentStep - 1) as Step);
    }
  };

  const canGoNext = () => {
    if (currentStep === 1) return isStep1Ready();
    if (currentStep === 2) return isStep2Ready();
    if (currentStep === 3) return isStep3Ready();
    return true; // Step 4 (Review) can always launch
  };

  const totalTrends = selectedSearchTrends.length + selectedYtTrends.length;

  return (
    <div className="flex flex-col h-full">
      {/* Horizontal Stepper */}
      <div className="px-6 py-4 border-b border-zinc-800 bg-zinc-900/50">
        <div className="flex items-center justify-between max-w-3xl mx-auto">
          {steps.map((step, idx) => {
            const status = getStepStatus(step.number);
            const isClickable = canProceedToStep(step.number) && !isRunning;

            return (
              <div key={step.number} className="flex items-center flex-1">
                {/* Step Circle */}
                <button
                  onClick={() => handleStepClick(step.number)}
                  disabled={!isClickable}
                  className={cn(
                    'flex items-center justify-center w-10 h-10 rounded-full font-semibold text-sm transition-all',
                    status === 'complete' && 'bg-green-600 text-white',
                    status === 'current' && 'bg-blue-600 text-white ring-4 ring-blue-600/30',
                    status === 'future' && 'bg-zinc-700 text-zinc-400',
                    isClickable && 'cursor-pointer hover:opacity-80',
                    !isClickable && 'cursor-not-allowed opacity-50'
                  )}
                >
                  {status === 'complete' ? (
                    <Check className="w-5 h-5" />
                  ) : (
                    step.number
                  )}
                </button>

                {/* Step Label */}
                <div className="ml-2 mr-4">
                  <div
                    className={cn(
                      'text-sm font-medium',
                      status === 'current' && 'text-blue-400',
                      status === 'complete' && 'text-green-400',
                      status === 'future' && 'text-zinc-500'
                    )}
                  >
                    {step.label}
                  </div>
                </div>

                {/* Connector Line */}
                {idx < steps.length - 1 && (
                  <div
                    className={cn(
                      'h-0.5 flex-1 transition-colors',
                      status === 'complete' ? 'bg-green-600' : 'bg-zinc-700'
                    )}
                  />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Step Content */}
      <div className="flex-1 overflow-auto p-6">
        <div className="max-w-3xl mx-auto">
          {/* Step 1: Campaign */}
          {currentStep === 1 && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-semibold text-zinc-100 mb-2">Campaign Details</h2>
                <p className="text-sm text-zinc-400">
                  Define your brand and product information. At least one of Brand or Product is required.
                </p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                {/* Brand */}
                <div>
                  <label className="mb-2 block text-xs font-medium text-zinc-400">
                    Brand <span className="text-red-500">*</span>
                  </label>
                  <div className="relative">
                    <input
                      type="text"
                      value={config.brand}
                      onChange={(e) => onConfigChange({ ...config, brand: e.target.value })}
                      disabled={isRunning}
                      placeholder="e.g., Google Pixel"
                      className={cn(
                        'flex h-9 w-full rounded-md border px-3 py-2 text-sm',
                        'text-zinc-50 placeholder:text-zinc-500 bg-zinc-900',
                        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500',
                        'disabled:opacity-50 disabled:cursor-not-allowed',
                        config.brand.trim() !== ''
                          ? 'border-zinc-700 border-l-4 border-l-green-500'
                          : 'border-zinc-700'
                      )}
                    />
                    {config.brand.trim() !== '' && (
                      <span className="absolute right-3 top-1/2 -translate-y-1/2 text-green-500 text-xs">
                        ✓
                      </span>
                    )}
                  </div>
                </div>

                {/* Product */}
                <div>
                  <label className="mb-2 block text-xs font-medium text-zinc-400">
                    Product <span className="text-red-500">*</span>
                  </label>
                  <div className="relative">
                    <input
                      type="text"
                      value={config.target_product}
                      onChange={(e) => onConfigChange({ ...config, target_product: e.target.value })}
                      disabled={isRunning}
                      placeholder="e.g., Pixel 9 Pro"
                      className={cn(
                        'flex h-9 w-full rounded-md border px-3 py-2 text-sm',
                        'text-zinc-50 placeholder:text-zinc-500 bg-zinc-900',
                        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500',
                        'disabled:opacity-50 disabled:cursor-not-allowed',
                        config.target_product.trim() !== ''
                          ? 'border-zinc-700 border-l-4 border-l-green-500'
                          : 'border-zinc-700'
                      )}
                    />
                    {config.target_product.trim() !== '' && (
                      <span className="absolute right-3 top-1/2 -translate-y-1/2 text-green-500 text-xs">
                        ✓
                      </span>
                    )}
                  </div>
                </div>

                {/* Audience */}
                <div>
                  <label className="mb-2 block text-xs font-medium text-zinc-400">
                    Target Audience
                  </label>
                  <div className="relative">
                    <input
                      type="text"
                      value={config.target_audience}
                      onChange={(e) => onConfigChange({ ...config, target_audience: e.target.value })}
                      disabled={isRunning}
                      placeholder="e.g., Tech-savvy millennials"
                      className={cn(
                        'flex h-9 w-full rounded-md border px-3 py-2 text-sm',
                        'text-zinc-50 placeholder:text-zinc-500 bg-zinc-900',
                        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500',
                        'disabled:opacity-50 disabled:cursor-not-allowed',
                        config.target_audience.trim() !== ''
                          ? 'border-zinc-700 border-l-4 border-l-green-500'
                          : 'border-zinc-700'
                      )}
                    />
                    {config.target_audience.trim() !== '' && (
                      <span className="absolute right-3 top-1/2 -translate-y-1/2 text-green-500 text-xs">
                        ✓
                      </span>
                    )}
                  </div>
                </div>

                {/* Selling Points */}
                <div>
                  <label className="mb-2 block text-xs font-medium text-zinc-400">
                    Key Selling Points
                  </label>
                  <div className="relative">
                    <textarea
                      value={config.key_selling_points}
                      onChange={(e) => onConfigChange({ ...config, key_selling_points: e.target.value })}
                      disabled={isRunning}
                      placeholder="e.g., AI camera, long battery"
                      rows={3}
                      className={cn(
                        'flex w-full rounded-md border px-3 py-2 text-sm',
                        'text-zinc-50 placeholder:text-zinc-500 bg-zinc-900',
                        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 resize-none',
                        'disabled:opacity-50 disabled:cursor-not-allowed',
                        config.key_selling_points.trim() !== ''
                          ? 'border-zinc-700 border-l-4 border-l-green-500'
                          : 'border-zinc-700'
                      )}
                    />
                    {config.key_selling_points.trim() !== '' && (
                      <span className="absolute right-3 top-2 text-green-500 text-xs">
                        ✓
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Step 2: Trends */}
          {currentStep === 2 && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-semibold text-zinc-100 mb-2">Trend Selection</h2>
                <p className="text-sm text-zinc-400 mb-4">
                  Select trends that are relevant to your brand and campaign. At least one trend is required.
                </p>
                <div className="p-3 bg-blue-950/30 border border-blue-800/50 rounded-lg">
                  <p className="text-xs text-blue-300">
                    <strong>Suggested selections:</strong> Choose trends that align with your brand values,
                    target audience interests, and product positioning. Consider both search trends (what people
                    are searching for) and YouTube trends (what content is popular).
                  </p>
                </div>
              </div>

              {/* Selected Trends Summary */}
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 bg-zinc-900 border border-zinc-800 rounded-lg">
                  <div className="text-xs text-zinc-500 uppercase tracking-wide mb-2">Google Search Trends</div>
                  <div className="text-2xl font-bold text-zinc-100">{selectedSearchTrends.length}</div>
                  <div className="text-xs text-zinc-400 mt-1">
                    {selectedSearchTrends.length === 0
                      ? 'No trends selected'
                      : selectedSearchTrends.length === 1
                      ? '1 trend selected'
                      : `${selectedSearchTrends.length} trends selected`}
                  </div>
                </div>

                <div className="p-4 bg-zinc-900 border border-zinc-800 rounded-lg">
                  <div className="text-xs text-zinc-500 uppercase tracking-wide mb-2">YouTube Trends</div>
                  <div className="text-2xl font-bold text-zinc-100">{selectedYtTrends.length}</div>
                  <div className="text-xs text-zinc-400 mt-1">
                    {selectedYtTrends.length === 0
                      ? 'No trends selected'
                      : selectedYtTrends.length === 1
                      ? '1 trend selected'
                      : `${selectedYtTrends.length} trends selected`}
                  </div>
                </div>
              </div>

              {/* Trend Details */}
              {totalTrends > 0 && (
                <div className="space-y-3">
                  {selectedSearchTrends.length > 0 && (
                    <div>
                      <div className="text-sm font-medium text-zinc-300 mb-2">
                        Selected Search Trends:
                      </div>
                      <div className="space-y-1">
                        {selectedSearchTrends.map((trend, idx) => (
                          <div
                            key={idx}
                            className="px-3 py-2 bg-zinc-900 border border-zinc-800 rounded text-sm text-zinc-300"
                          >
                            <span className="font-medium">#{trend.rank}</span> {trend.title}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {selectedYtTrends.length > 0 && (
                    <div>
                      <div className="text-sm font-medium text-zinc-300 mb-2">
                        Selected YouTube Trends:
                      </div>
                      <div className="space-y-1">
                        {selectedYtTrends.map((trend, idx) => (
                          <div
                            key={idx}
                            className="px-3 py-2 bg-zinc-900 border border-zinc-800 rounded text-sm text-zinc-300"
                          >
                            <span className="font-medium">#{trend.rank}</span> {trend.title}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Brand Safety Guardrail */}
              <TrendSafetyGuardrail
                searchTrends={selectedSearchTrends}
                ytTrends={selectedYtTrends}
                brand={config.brand}
                targetAudience={config.target_audience}
              />

              {/* Link to trend selector (if needed) */}
              {totalTrends === 0 && (
                <div className="p-4 bg-amber-950/30 border border-amber-800/50 rounded-lg">
                  <p className="text-sm text-amber-300">
                    You haven't selected any trends yet. Please go to the Trends tab to select relevant
                    search and YouTube trends for your campaign.
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Step 3: Settings */}
          {currentStep === 3 && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-semibold text-zinc-100 mb-2">Pipeline Settings</h2>
                <p className="text-sm text-zinc-400">
                  Configure the output format and execution mode for your marketing pipeline.
                </p>
              </div>

              {/* Commercial Duration */}
              <div>
                <label className="mb-2 block text-sm font-medium text-zinc-300">
                  Commercial Duration
                </label>
                <p className="text-xs text-zinc-500 mb-3">
                  Select the target length for the final video commercial.
                </p>
                <div className="flex gap-3">
                  {[10, 15, 30].map((duration) => (
                    <button
                      key={duration}
                      onClick={() => onDurationChange(duration as 10 | 15 | 30)}
                      disabled={isRunning}
                      className={cn(
                        'flex-1 px-4 py-3 rounded-lg border-2 text-sm font-medium transition-all',
                        'disabled:opacity-50 disabled:cursor-not-allowed',
                        commercialDuration === duration
                          ? 'border-blue-600 bg-blue-600/20 text-blue-400'
                          : 'border-zinc-700 bg-zinc-900 text-zinc-400 hover:border-zinc-600'
                      )}
                    >
                      {duration} seconds
                    </button>
                  ))}
                </div>
              </div>

              {/* Autopilot Mode */}
              <div className="p-4 bg-zinc-900 border border-zinc-800 rounded-lg">
                <div
                  className={cn(
                    "flex items-center justify-between",
                    !isRunning && "cursor-pointer"
                  )}
                  onClick={() => !isRunning && onAutopilotChange(!autopilot)}
                >
                  <div className="flex-1">
                    <label className="text-sm font-medium text-zinc-300 block">
                      AI Autopilot Mode
                    </label>
                    <p className="text-xs text-zinc-500 mt-1">
                      Auto-approve all agent outputs without pausing. When enabled, the pipeline runs
                      end-to-end without requiring manual approval at each stage.
                    </p>
                  </div>
                  <button
                    disabled={isRunning}
                    className={cn(
                      'relative inline-flex h-6 w-11 items-center rounded-full transition-colors ml-4 flex-shrink-0 pointer-events-none',
                      'disabled:opacity-50 disabled:cursor-not-allowed',
                      autopilot ? 'bg-blue-600' : 'bg-zinc-700'
                    )}
                  >
                    <span
                      className={cn(
                        'inline-block h-4 w-4 transform rounded-full bg-white transition-transform',
                        autopilot ? 'translate-x-6' : 'translate-x-1'
                      )}
                    />
                  </button>
                </div>
                {autopilot && (
                  <div className="mt-3 p-2 bg-blue-950/30 border border-blue-800/50 rounded text-xs text-blue-300">
                    Autopilot is enabled. The pipeline will run automatically without manual approvals.
                  </div>
                )}
              </div>

              {/* Active Rubrics Info */}
              {activeRubrics.length > 0 && (
                <div className="p-4 bg-green-950/20 border border-green-800/50 rounded-lg">
                  <div className="text-sm font-medium text-green-300 mb-2">
                    Focus Group Evaluation
                  </div>
                  <p className="text-xs text-green-400/80">
                    {activeRubrics.length} evaluation {activeRubrics.length === 1 ? 'rubric' : 'rubrics'} selected:{' '}
                    {activeRubrics.map((r) => r.name).join(', ')}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Step 4: Review & Launch */}
          {currentStep === 4 && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-semibold text-zinc-100 mb-2">Review & Launch</h2>
                <p className="text-sm text-zinc-400">
                  Review your configuration and launch the marketing pipeline.
                </p>
              </div>

              {/* Summary Cards */}
              <div className="space-y-4">
                {/* Campaign Summary */}
                <div className="p-4 bg-zinc-900 border border-zinc-800 rounded-lg">
                  <div className="text-sm font-semibold text-zinc-300 mb-3 flex items-center gap-2">
                    <span className={cn(
                      'flex items-center justify-center w-6 h-6 rounded-full text-white text-xs',
                      confirmedSteps.has(1) ? 'bg-green-600' : 'bg-zinc-600'
                    )}>
                      {confirmedSteps.has(1) ? <Check className="w-3.5 h-3.5" /> : '1'}
                    </span>
                    Campaign Details
                  </div>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <div className="text-xs text-zinc-500">Brand</div>
                      <div className="text-zinc-200">{config.brand || '—'}</div>
                    </div>
                    <div>
                      <div className="text-xs text-zinc-500">Product</div>
                      <div className="text-zinc-200">{config.target_product || '—'}</div>
                    </div>
                    <div>
                      <div className="text-xs text-zinc-500">Audience</div>
                      <div className="text-zinc-200">{config.target_audience || '—'}</div>
                    </div>
                    <div>
                      <div className="text-xs text-zinc-500">Selling Points</div>
                      <div className="text-zinc-200 line-clamp-2">
                        {config.key_selling_points || '—'}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Trends Summary */}
                <div className="p-4 bg-zinc-900 border border-zinc-800 rounded-lg">
                  <div className="text-sm font-semibold text-zinc-300 mb-3 flex items-center gap-2">
                    <span className={cn(
                      'flex items-center justify-center w-6 h-6 rounded-full text-white text-xs',
                      confirmedSteps.has(2) ? 'bg-green-600' : 'bg-zinc-600'
                    )}>
                      {confirmedSteps.has(2) ? <Check className="w-3.5 h-3.5" /> : '2'}
                    </span>
                    Selected Trends
                  </div>
                  <div className="flex gap-4 text-sm">
                    <div>
                      <div className="text-xs text-zinc-500">Search Trends</div>
                      <div className="text-zinc-200 font-medium">{selectedSearchTrends.length}</div>
                    </div>
                    <div>
                      <div className="text-xs text-zinc-500">YouTube Trends</div>
                      <div className="text-zinc-200 font-medium">{selectedYtTrends.length}</div>
                    </div>
                    <div>
                      <div className="text-xs text-zinc-500">Total</div>
                      <div className="text-zinc-200 font-medium">{totalTrends}</div>
                    </div>
                  </div>
                </div>

                {/* Settings Summary */}
                <div className="p-4 bg-zinc-900 border border-zinc-800 rounded-lg">
                  <div className="text-sm font-semibold text-zinc-300 mb-3 flex items-center gap-2">
                    <span className={cn(
                      'flex items-center justify-center w-6 h-6 rounded-full text-white text-xs',
                      confirmedSteps.has(3) ? 'bg-green-600' : 'bg-zinc-600'
                    )}>
                      {confirmedSteps.has(3) ? <Check className="w-3.5 h-3.5" /> : '3'}
                    </span>
                    Pipeline Settings
                  </div>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <div className="text-xs text-zinc-500">Commercial Duration</div>
                      <div className="text-zinc-200">{commercialDuration} seconds</div>
                    </div>
                    <div>
                      <div className="text-xs text-zinc-500">Execution Mode</div>
                      <div className={cn(
                        'font-medium',
                        autopilot ? 'text-blue-400' : 'text-zinc-200'
                      )}>
                        {autopilot ? 'Autopilot (Auto-approve)' : 'Manual Approval'}
                      </div>
                    </div>
                    {activeRubrics.length > 0 && (
                      <div className="col-span-2">
                        <div className="text-xs text-zinc-500">Evaluation Rubrics</div>
                        <div className="text-zinc-200">
                          {activeRubrics.map((r) => r.name).join(', ')}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Launch Button */}
              <div className="pt-4">
                <button
                  onClick={onLaunch}
                  disabled={isRunning}
                  className={cn(
                    'w-full flex items-center justify-center gap-3 px-6 py-4 rounded-lg text-base font-semibold transition-all',
                    'disabled:opacity-50 disabled:cursor-not-allowed',
                    isRunning
                      ? 'bg-zinc-700 text-zinc-400'
                      : 'bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 text-white shadow-lg shadow-green-900/50'
                  )}
                >
                  <Play className="w-5 h-5" />
                  Launch Marketing Pipeline
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Navigation Footer — sticky so it's always visible */}
      <div className="sticky bottom-0 px-6 py-3 border-t border-zinc-800 bg-zinc-900 z-10">
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <button
            onClick={handleBack}
            disabled={currentStep === 1 || isRunning}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all',
              'disabled:opacity-50 disabled:cursor-not-allowed',
              currentStep === 1 || isRunning
                ? 'bg-zinc-800 text-zinc-500'
                : 'bg-zinc-700 text-zinc-200 hover:bg-zinc-600'
            )}
          >
            <ChevronLeft className="w-4 h-4" />
            Back
          </button>

          <div className="text-sm text-zinc-500">
            Step {currentStep} of 4
          </div>

          <button
            onClick={handleNext}
            disabled={!canGoNext() || isRunning}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all',
              'disabled:opacity-50 disabled:cursor-not-allowed',
              !canGoNext() || isRunning
                ? 'bg-zinc-800 text-zinc-500'
                : currentStep === 4
                ? 'bg-green-600 text-white hover:bg-green-500'
                : 'bg-blue-600 text-white hover:bg-blue-500'
            )}
          >
            {currentStep === 4 ? (
              <>
                <Play className="w-4 h-4" />
                Launch Pipeline
              </>
            ) : (
              <>
                Next
                <ChevronRight className="w-4 h-4" />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
