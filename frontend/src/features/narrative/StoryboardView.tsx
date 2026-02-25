import { useState } from 'react';
import type { Scene } from './types';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';

interface StoryboardViewProps {
  scenes: Scene[];
  onReorder: (startIndex: number, endIndex: number) => void;
  onUpdateScene: (sceneId: string, updates: Partial<Scene>) => void;
}

const NARRATIVE_BEAT_COLORS: Record<
  Scene['narrativeBeat'],
  { bg: string; text: string }
> = {
  setup: { bg: 'bg-blue-600', text: 'Setup' },
  rising_action: { bg: 'bg-yellow-600', text: 'Rising Action' },
  climax: { bg: 'bg-red-600', text: 'Climax' },
  resolution: { bg: 'bg-green-600', text: 'Resolution' },
};

export function StoryboardView({
  scenes,
  onReorder,
  onUpdateScene,
}: StoryboardViewProps) {
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);
  const [editingSceneId, setEditingSceneId] = useState<string | null>(null);
  const [editDescription, setEditDescription] = useState('');

  const handleDragStart = (index: number) => {
    setDraggedIndex(index);
  };

  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault();
    if (draggedIndex === null || draggedIndex === index) return;

    onReorder(draggedIndex, index);
    setDraggedIndex(index);
  };

  const handleDragEnd = () => {
    setDraggedIndex(null);
  };

  const handleStartEdit = (scene: Scene) => {
    setEditingSceneId(scene.id);
    setEditDescription(scene.description);
  };

  const handleSaveEdit = (sceneId: string) => {
    onUpdateScene(sceneId, { description: editDescription });
    setEditingSceneId(null);
    setEditDescription('');
  };

  const handleCancelEdit = () => {
    setEditingSceneId(null);
    setEditDescription('');
  };

  if (scenes.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center rounded-lg border border-dashed border-zinc-700 bg-zinc-900/50">
        <p className="text-zinc-500">No scenes in storyboard yet</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Storyboard Grid */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {scenes.map((scene, index) => {
          const beatConfig = NARRATIVE_BEAT_COLORS[scene.narrativeBeat];
          const isEditing = editingSceneId === scene.id;

          return (
            <Card
              key={scene.id}
              draggable={!isEditing}
              onDragStart={() => handleDragStart(index)}
              onDragOver={(e) => handleDragOver(e, index)}
              onDragEnd={handleDragEnd}
              className={`cursor-move transition-all ${
                draggedIndex === index ? 'opacity-50' : ''
              } ${isEditing ? 'ring-2 ring-blue-500' : ''}`}
            >
              {/* Scene Number & Beat */}
              <div className="flex items-center justify-between border-b border-zinc-800 p-3">
                <div className="flex items-center gap-2">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-zinc-800 text-sm font-bold text-zinc-100">
                    {scene.sceneNumber}
                  </div>
                  <span className="text-sm font-medium text-zinc-300">
                    Scene {scene.sceneNumber}
                  </span>
                </div>
                <Badge variant="default" className={beatConfig.bg}>
                  {beatConfig.text}
                </Badge>
              </div>

              {/* Frame Preview */}
              <div className="relative aspect-video w-full overflow-hidden bg-zinc-900">
                {scene.frameUrl ? (
                  <img
                    src={scene.frameUrl}
                    alt={`Scene ${scene.sceneNumber}`}
                    className="h-full w-full object-cover"
                  />
                ) : (
                  <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-zinc-800 to-zinc-900">
                    <svg
                      className="h-12 w-12 text-zinc-700"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                      />
                    </svg>
                  </div>
                )}

                {/* Duration Badge */}
                <div className="absolute bottom-2 right-2 rounded bg-black/70 px-2 py-1 text-xs font-medium text-white">
                  {scene.duration}s
                </div>
              </div>

              {/* Description */}
              <div className="p-3">
                {isEditing ? (
                  <div className="space-y-2">
                    <textarea
                      value={editDescription}
                      onChange={(e) => setEditDescription(e.target.value)}
                      className="w-full rounded border border-zinc-700 bg-zinc-800 p-2 text-sm text-zinc-100 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                      rows={3}
                      placeholder="Scene description..."
                    />
                    <div className="flex gap-2">
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={() => handleSaveEdit(scene.id)}
                        className="flex-1"
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
                  <>
                    <p className="mb-2 line-clamp-3 text-sm text-zinc-300">
                      {scene.description}
                    </p>
                    <button
                      onClick={() => handleStartEdit(scene)}
                      className="text-xs text-blue-400 hover:text-blue-300"
                    >
                      Edit description
                    </button>
                  </>
                )}
              </div>
            </Card>
          );
        })}
      </div>

      {/* Flow Arrows (visual hint) */}
      <div className="flex items-center justify-center gap-2 text-zinc-600">
        <span className="text-xs">Drag to reorder scenes</span>
        <svg
          className="h-4 w-4"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M8 9l4-4 4 4m0 6l-4 4-4-4"
          />
        </svg>
      </div>
    </div>
  );
}
