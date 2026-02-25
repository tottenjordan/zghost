import { useState } from 'react';
import { Input } from '../../components/ui/Input';
import { Textarea } from '../../components/ui/Textarea';
import { Slider } from '../../components/ui/Slider';
import { Button } from '../../components/ui/Button';
import type { ExtendedCriterion, ScaleType } from './rubric-templates';

interface CriteriaBuilderProps {
  criterion: ExtendedCriterion;
  onChange: (criterion: ExtendedCriterion) => void;
  onDelete: () => void;
}

export function CriteriaBuilder({ criterion, onChange, onDelete }: CriteriaBuilderProps) {
  const [showDelete, setShowDelete] = useState(false);
  const [expanded, setExpanded] = useState(false);

  const handleScaleTypeChange = (type: ScaleType) => {
    let newScale = { ...criterion.scale, type };

    switch (type) {
      case 'likert':
        newScale = {
          type: 'likert',
          min: 1,
          max: 5,
          labels: {
            1: 'Poor',
            2: 'Below Average',
            3: 'Average',
            4: 'Above Average',
            5: 'Excellent',
          },
        };
        break;
      case 'numeric':
        newScale = {
          type: 'numeric',
          min: 1,
          max: 10,
          labels: {},
        };
        break;
      case 'pass-fail':
        newScale = {
          type: 'pass-fail',
          min: 0,
          max: 1,
          labels: { 0: 'Fail', 1: 'Pass' },
        };
        break;
    }

    onChange({ ...criterion, scale: newScale });
  };

  const handleLabelChange = (value: number, label: string) => {
    const newLabels = { ...criterion.scale.labels, [value]: label };
    onChange({
      ...criterion,
      scale: { ...criterion.scale, labels: newLabels },
    });
  };

  return (
    <div className="rounded-lg border border-zinc-700 bg-zinc-800 p-4">
      <div className="flex items-start gap-3">
        <div className="flex cursor-grab items-center text-zinc-500">
          <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
            <path d="M7 2a2 2 0 1 0 .001 4.001A2 2 0 0 0 7 2zm0 6a2 2 0 1 0 .001 4.001A2 2 0 0 0 7 8zm0 6a2 2 0 1 0 .001 4.001A2 2 0 0 0 7 14zm6-8a2 2 0 1 0-.001-4.001A2 2 0 0 0 13 6zm0 2a2 2 0 1 0 .001 4.001A2 2 0 0 0 13 8zm0 6a2 2 0 1 0 .001 4.001A2 2 0 0 0 13 14z" />
          </svg>
        </div>

        <div className="flex-1 space-y-3">
          <div className="grid gap-3 md:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm font-medium text-zinc-300">
                Criterion Name
              </label>
              <Input
                value={criterion.name}
                onChange={(e) => onChange({ ...criterion, name: e.target.value })}
                placeholder="e.g., Creativity"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-zinc-300">
                Scale Type
              </label>
              <select
                value={criterion.scale.type}
                onChange={(e) => handleScaleTypeChange(e.target.value as ScaleType)}
                className="flex h-10 w-full rounded-md border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
              >
                <option value="likert">Likert (1-5)</option>
                <option value="numeric">Numeric (1-10)</option>
                <option value="pass-fail">Pass/Fail</option>
              </select>
            </div>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-zinc-300">
              Description
            </label>
            <Textarea
              value={criterion.description}
              onChange={(e) => onChange({ ...criterion, description: e.target.value })}
              placeholder="Describe what this criterion evaluates"
              rows={2}
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-zinc-300">
              Weight: {criterion.weight}%
            </label>
            <Slider
              min={0}
              max={100}
              step={5}
              value={criterion.weight}
              onChange={(e) => onChange({ ...criterion, weight: Number(e.target.value) })}
            />
          </div>

          {criterion.scale.labels && Object.keys(criterion.scale.labels).length > 0 && (
            <div>
              <button
                onClick={() => setExpanded(!expanded)}
                className="mb-2 flex items-center gap-1 text-sm font-medium text-zinc-300 hover:text-zinc-50"
              >
                <svg
                  className={`h-4 w-4 transition-transform ${expanded ? 'rotate-90' : ''}`}
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path d="M6 6L14 10L6 14V6Z" />
                </svg>
                Scale Labels
              </button>

              {expanded && (
                <div className="space-y-2 rounded border border-zinc-700 bg-zinc-900 p-3">
                  {Object.entries(criterion.scale.labels).map(([value, label]) => (
                    <div key={value} className="flex items-center gap-2">
                      <span className="w-8 text-sm text-zinc-400">{value}:</span>
                      <Input
                        value={label}
                        onChange={(e) => handleLabelChange(Number(value), e.target.value)}
                        placeholder={`Label for ${value}`}
                        className="flex-1"
                      />
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        <div>
          {showDelete ? (
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="danger"
                onClick={onDelete}
              >
                Confirm
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setShowDelete(false)}
              >
                Cancel
              </Button>
            </div>
          ) : (
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setShowDelete(true)}
            >
              Delete
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
