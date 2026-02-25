import { useState } from 'react';
import type { NarrativeArc as NarrativeArcType, Scene } from './types';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';

interface NarrativeArcProps {
  narrativeArc?: NarrativeArcType;
  scenes: Scene[];
  onUpdate: (arc: Partial<NarrativeArcType>) => void;
}

const DEFAULT_ARC: NarrativeArcType = {
  setup: 'Introduce the world and the character',
  risingAction: 'Build tension and develop the situation',
  climax: 'Reach the peak moment of the story',
  resolution: 'Resolve the story and deliver the message',
};

export function NarrativeArc({ narrativeArc, scenes, onUpdate }: NarrativeArcProps) {
  const [editingBeat, setEditingBeat] = useState<keyof NarrativeArcType | null>(
    null
  );
  const [editValue, setEditValue] = useState('');

  const arc = narrativeArc || DEFAULT_ARC;

  const handleStartEdit = (beat: keyof NarrativeArcType) => {
    setEditingBeat(beat);
    setEditValue(arc[beat]);
  };

  const handleSaveEdit = () => {
    if (editingBeat) {
      onUpdate({ [editingBeat]: editValue });
      setEditingBeat(null);
      setEditValue('');
    }
  };

  const handleCancelEdit = () => {
    setEditingBeat(null);
    setEditValue('');
  };

  const getBeatScenes = (beat: keyof NarrativeArcType): Scene[] => {
    const beatMap: Record<keyof NarrativeArcType, Scene['narrativeBeat']> = {
      setup: 'setup',
      risingAction: 'rising_action',
      climax: 'climax',
      resolution: 'resolution',
    };
    return scenes.filter((s) => s.narrativeBeat === beatMap[beat]);
  };

  const arcPoints: Array<{
    key: keyof NarrativeArcType;
    label: string;
    color: string;
    position: string;
  }> = [
    { key: 'setup', label: 'Setup', color: 'bg-blue-500', position: 'left-[5%]' },
    {
      key: 'risingAction',
      label: 'Rising Action',
      color: 'bg-yellow-500',
      position: 'left-[35%]',
    },
    {
      key: 'climax',
      label: 'Climax',
      color: 'bg-red-500',
      position: 'left-[65%]',
    },
    {
      key: 'resolution',
      label: 'Resolution',
      color: 'bg-green-500',
      position: 'left-[90%]',
    },
  ];

  return (
    <Card className="bg-zinc-900">
      <CardHeader>
        <CardTitle>Narrative Arc</CardTitle>
      </CardHeader>
      <CardContent>
        {/* Arc Visualization */}
        <div className="relative mb-8 h-48 rounded-lg bg-black p-4">
          {/* Arc curve (SVG) */}
          <svg className="absolute inset-0 h-full w-full" viewBox="0 0 400 150">
            <path
              d="M 20 130 Q 100 120, 140 80 T 280 40 T 380 110"
              stroke="#3b82f6"
              strokeWidth="2"
              fill="none"
              strokeDasharray="4 2"
              opacity="0.5"
            />
          </svg>

          {/* Beat points */}
          {arcPoints.map((point, idx) => {
            const beatScenes = getBeatScenes(point.key);
            const heights = ['bottom-8', 'bottom-16', 'bottom-24', 'bottom-20'];

            return (
              <div
                key={point.key}
                className={`absolute ${point.position} ${heights[idx]} -translate-x-1/2`}
              >
                <div className="relative flex flex-col items-center">
                  {/* Point */}
                  <div
                    className={`h-4 w-4 rounded-full ${point.color} ring-4 ring-black`}
                  />

                  {/* Label */}
                  <div className="mt-2 rounded bg-zinc-800 px-2 py-1">
                    <p className="whitespace-nowrap text-xs font-medium text-zinc-100">
                      {point.label}
                    </p>
                    <p className="text-xs text-zinc-500">
                      {beatScenes.length} scene{beatScenes.length !== 1 ? 's' : ''}
                    </p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Beat Details */}
        <div className="space-y-3">
          {arcPoints.map((point) => {
            const isEditing = editingBeat === point.key;
            const beatScenes = getBeatScenes(point.key);

            return (
              <div
                key={point.key}
                className="rounded-lg border border-zinc-800 bg-black p-3"
              >
                <div className="mb-2 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className={`h-3 w-3 rounded-full ${point.color}`} />
                    <h4 className="text-sm font-medium text-zinc-100">
                      {point.label}
                    </h4>
                    <span className="text-xs text-zinc-500">
                      ({beatScenes.length} scene{beatScenes.length !== 1 ? 's' : ''})
                    </span>
                  </div>
                  {!isEditing && (
                    <button
                      onClick={() => handleStartEdit(point.key)}
                      className="text-xs text-blue-400 hover:text-blue-300"
                    >
                      Edit
                    </button>
                  )}
                </div>

                {isEditing ? (
                  <div className="space-y-2">
                    <textarea
                      value={editValue}
                      onChange={(e) => setEditValue(e.target.value)}
                      className="w-full rounded border border-zinc-700 bg-zinc-800 p-2 text-sm text-zinc-100 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                      rows={2}
                    />
                    <div className="flex gap-2">
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={handleSaveEdit}
                      >
                        Save
                      </Button>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={handleCancelEdit}
                      >
                        Cancel
                      </Button>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-zinc-400">{arc[point.key]}</p>
                )}
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
