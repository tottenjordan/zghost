import { useState } from 'react';
import { Slider } from '../../components/ui/Slider';
import { Textarea } from '../../components/ui/Textarea';
import type { ExtendedCriterion } from './rubric-templates';

interface RatingControlsProps {
  criterion: ExtendedCriterion;
  value?: number;
  comment?: string;
  onChange: (value: number) => void;
  onCommentChange: (comment: string) => void;
}

export function RatingControls({
  criterion,
  value,
  comment,
  onChange,
  onCommentChange,
}: RatingControlsProps) {
  const [showNotes, setShowNotes] = useState(false);
  const [showDescription, setShowDescription] = useState(false);

  const getScoreColor = (score: number) => {
    const normalized = (score - criterion.scale.min) / (criterion.scale.max - criterion.scale.min);
    if (normalized < 0.4) return 'text-red-400';
    if (normalized < 0.7) return 'text-yellow-400';
    return 'text-green-400';
  };

  const renderControl = () => {
    switch (criterion.scale.type) {
      case 'likert':
        return (
          <div className="space-y-2">
            <div className="flex justify-between gap-2">
              {Array.from({ length: criterion.scale.max }, (_, i) => i + 1).map((rating) => (
                <button
                  key={rating}
                  onClick={() => onChange(rating)}
                  className={`flex-1 rounded-lg border px-3 py-2 text-center transition-colors ${
                    value === rating
                      ? 'border-blue-500 bg-blue-600 text-white'
                      : 'border-zinc-700 bg-zinc-800 text-zinc-300 hover:border-zinc-600 hover:bg-zinc-700'
                  }`}
                >
                  <div className="font-semibold">{rating}</div>
                  {criterion.scale.labels?.[rating] && (
                    <div className="text-xs opacity-80">
                      {criterion.scale.labels[rating]}
                    </div>
                  )}
                </button>
              ))}
            </div>
          </div>
        );

      case 'numeric':
        return (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm text-zinc-400">{criterion.scale.min}</span>
              <span className={`text-lg font-bold ${value !== undefined ? getScoreColor(value) : 'text-zinc-500'}`}>
                {value !== undefined ? value : '-'}
              </span>
              <span className="text-sm text-zinc-400">{criterion.scale.max}</span>
            </div>
            <Slider
              min={criterion.scale.min}
              max={criterion.scale.max}
              step={1}
              value={value || criterion.scale.min}
              onChange={(e) => onChange(Number(e.target.value))}
              className="w-full"
            />
          </div>
        );

      case 'pass-fail':
        return (
          <div className="flex gap-3">
            <button
              onClick={() => onChange(0)}
              className={`flex-1 rounded-lg border px-4 py-3 text-center transition-colors ${
                value === 0
                  ? 'border-red-500 bg-red-600 text-white'
                  : 'border-zinc-700 bg-zinc-800 text-zinc-300 hover:border-zinc-600 hover:bg-zinc-700'
              }`}
            >
              Fail
            </button>
            <button
              onClick={() => onChange(1)}
              className={`flex-1 rounded-lg border px-4 py-3 text-center transition-colors ${
                value === 1
                  ? 'border-green-500 bg-green-600 text-white'
                  : 'border-zinc-700 bg-zinc-800 text-zinc-300 hover:border-zinc-600 hover:bg-zinc-700'
              }`}
            >
              Pass
            </button>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="space-y-3 rounded-lg border border-zinc-700 bg-zinc-800 p-4">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h4 className="font-medium text-zinc-50">{criterion.name}</h4>
            <button
              onClick={() => setShowDescription(!showDescription)}
              className="text-zinc-500 hover:text-zinc-300"
              title="Show description"
            >
              <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                  clipRule="evenodd"
                />
              </svg>
            </button>
          </div>
          {showDescription && (
            <p className="mt-1 text-sm text-zinc-400">{criterion.description}</p>
          )}
        </div>
        <span className="text-sm text-zinc-500">Weight: {criterion.weight}%</span>
      </div>

      {renderControl()}

      <button
        onClick={() => setShowNotes(!showNotes)}
        className="text-sm text-zinc-400 hover:text-zinc-300"
      >
        {showNotes ? '▼' : '▶'} Notes
      </button>

      {showNotes && (
        <Textarea
          value={comment || ''}
          onChange={(e) => onCommentChange(e.target.value)}
          placeholder="Add notes about this rating..."
          rows={2}
          className="text-sm"
        />
      )}
    </div>
  );
}
