import { useState } from 'react';
import { Star } from 'lucide-react';
import type { ExtendedRubric } from '../rating/rubric-templates';
import { cn } from '../../lib/utils';

interface EvaluationPanelProps {
  sessionState: Record<string, any>;
  rubrics: ExtendedRubric[];
}

export function EvaluationPanel({ sessionState, rubrics }: EvaluationPanelProps) {
  const [scores, setScores] = useState<Record<string, number>>({});
  const [activeTab, setActiveTab] = useState(0);

  const hasReport = !!sessionState.combined_final_cited_report;
  const hasAdCopies = !!sessionState.final_select_ad_copies;
  const hasVisuals = !!sessionState.final_visual_concepts;
  const hasArtifacts = hasReport || hasAdCopies || hasVisuals;

  if (rubrics.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8 text-center">
        <Star className="w-10 h-10 text-zinc-600 mb-3" />
        <p className="text-sm text-zinc-500">No rubric selected</p>
        <p className="text-xs text-zinc-600 mt-1">
          Select an evaluation rubric in the Configure page to score pipeline outputs
        </p>
      </div>
    );
  }

  if (!hasArtifacts) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8 text-center">
        <Star className="w-10 h-10 text-zinc-600 mb-3" />
        <p className="text-sm text-zinc-500">No artifacts to evaluate yet</p>
        <p className="text-xs text-zinc-600 mt-1">
          Run the pipeline to generate content for evaluation
        </p>
      </div>
    );
  }

  const handleScoreChange = (criterionId: string, score: number) => {
    setScores(prev => ({ ...prev, [criterionId]: score }));
  };

  const rubric = rubrics[activeTab] || rubrics[0];
  const totalWeight = rubric.criteria.reduce((sum, c) => sum + c.weight, 0);
  const scoredCriteria = rubric.criteria.filter(c => scores[c.id] !== undefined);
  const overallScore = scoredCriteria.length > 0
    ? scoredCriteria.reduce((sum, c) => {
        const normalized = ((scores[c.id] - c.scale.min) / (c.scale.max - c.scale.min)) * 100;
        return sum + normalized * (c.weight / totalWeight);
      }, 0)
    : null;

  return (
    <div className="p-3 space-y-4 overflow-y-auto h-full">
      {/* Rubric tabs (when multiple) */}
      {rubrics.length > 1 && (
        <div className="flex gap-1 border-b border-zinc-800 pb-2">
          {rubrics.map((r, i) => (
            <button
              key={r.id}
              onClick={() => setActiveTab(i)}
              className={cn(
                'px-3 py-1 rounded-t text-xs font-medium transition-colors',
                i === activeTab
                  ? 'bg-zinc-800 text-zinc-200 border border-b-0 border-zinc-700'
                  : 'text-zinc-500 hover:text-zinc-400'
              )}
            >
              {r.name}
            </button>
          ))}
        </div>
      )}

      {/* Rubric header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-medium text-zinc-300">{rubric.name}</h3>
          <p className="text-xs text-zinc-500">{rubric.description}</p>
        </div>
        {overallScore !== null && (
          <div className="text-right">
            <div className="text-xs text-zinc-500">Overall</div>
            <div className={cn(
              'text-lg font-bold',
              overallScore >= 70 ? 'text-green-400' :
              overallScore >= 40 ? 'text-yellow-400' : 'text-red-400'
            )}>
              {overallScore.toFixed(0)}%
            </div>
          </div>
        )}
      </div>

      {/* Artifact summary */}
      <div className="flex flex-wrap gap-1.5 text-xs">
        {hasReport && <span className="px-2 py-0.5 rounded bg-blue-950/50 border border-blue-800/50 text-blue-400">Research Report</span>}
        {hasAdCopies && <span className="px-2 py-0.5 rounded bg-purple-950/50 border border-purple-800/50 text-purple-400">Ad Copies</span>}
        {hasVisuals && <span className="px-2 py-0.5 rounded bg-green-950/50 border border-green-800/50 text-green-400">Visual Concepts</span>}
      </div>

      {/* Criteria scoring */}
      <div className="space-y-3">
        {rubric.criteria.map((criterion) => {
          const currentScore = scores[criterion.id];
          const labels = criterion.scale.labels || {};

          return (
            <div key={criterion.id} className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-3">
              <div className="flex items-start justify-between mb-2">
                <div>
                  <h4 className="text-sm font-medium text-zinc-200">{criterion.name}</h4>
                  <p className="text-xs text-zinc-500">{criterion.description}</p>
                </div>
                <span className="text-xs text-zinc-600 ml-2 whitespace-nowrap">{criterion.weight}%</span>
              </div>

              {/* Score progress bar */}
              {currentScore !== undefined && (
                <div className="mb-2">
                  <div className="h-1.5 rounded-full bg-zinc-800 overflow-hidden">
                    <div
                      className={cn(
                        'h-full rounded-full transition-all duration-300',
                        currentScore >= 4 ? 'bg-green-500' :
                        currentScore >= 3 ? 'bg-yellow-500' : 'bg-red-500'
                      )}
                      style={{ width: `${((currentScore - criterion.scale.min) / (criterion.scale.max - criterion.scale.min)) * 100}%` }}
                    />
                  </div>
                </div>
              )}

              {/* Score buttons */}
              <div className="flex gap-1">
                {Array.from(
                  { length: criterion.scale.max - criterion.scale.min + 1 },
                  (_, i) => criterion.scale.min + i
                ).map((value) => (
                  <button
                    key={value}
                    onClick={() => handleScoreChange(criterion.id, value)}
                    className={cn(
                      'flex-1 rounded px-1 py-1.5 text-center text-xs transition-colors',
                      currentScore === value
                        ? 'bg-blue-600 text-white border border-blue-500'
                        : 'bg-zinc-800 text-zinc-400 border border-zinc-700 hover:bg-zinc-700 hover:text-zinc-300'
                    )}
                    title={labels[value] || String(value)}
                  >
                    <div className="font-medium">{value}</div>
                    {labels[value] && (
                      <div className="text-[9px] mt-0.5 truncate opacity-70">{labels[value]}</div>
                    )}
                  </button>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
