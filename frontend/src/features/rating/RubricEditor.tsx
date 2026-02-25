import { useState } from 'react';
import { Input } from '../../components/ui/Input';
import { Textarea } from '../../components/ui/Textarea';
import { Button } from '../../components/ui/Button';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { CriteriaBuilder } from './CriteriaBuilder';
import type { ExtendedRubric, ExtendedCriterion } from './rubric-templates';

interface RubricEditorProps {
  rubric?: ExtendedRubric;
  onSave: (rubric: Omit<ExtendedRubric, 'id'>) => void;
  onCancel: () => void;
}

export function RubricEditor({ rubric, onSave, onCancel }: RubricEditorProps) {
  const [name, setName] = useState(rubric?.name || '');
  const [description, setDescription] = useState(rubric?.description || '');
  const [criteria, setCriteria] = useState<ExtendedCriterion[]>(
    rubric?.criteria || []
  );
  const [showPreview, setShowPreview] = useState(false);

  const handleAddCriterion = () => {
    const newCriterion: ExtendedCriterion = {
      id: `criterion-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      name: '',
      description: '',
      weight: 20,
      scale: {
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
      },
    };
    setCriteria([...criteria, newCriterion]);
  };

  const handleCriterionChange = (index: number, criterion: ExtendedCriterion) => {
    const updated = [...criteria];
    updated[index] = criterion;
    setCriteria(updated);
  };

  const handleCriterionDelete = (index: number) => {
    setCriteria(criteria.filter((_, i) => i !== index));
  };

  const handleSave = () => {
    onSave({ name, description, criteria });
  };

  const totalWeight = criteria.reduce((sum, c) => sum + c.weight, 0);
  const isValid = name.trim() && criteria.length > 0 && totalWeight === 100;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-zinc-50">
          {rubric ? 'Edit Rubric' : 'Create New Rubric'}
        </h2>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setShowPreview(!showPreview)}
        >
          {showPreview ? 'Edit Mode' : 'Preview'}
        </Button>
      </div>

      {showPreview ? (
        <Card>
          <CardHeader>
            <CardTitle>{name || 'Untitled Rubric'}</CardTitle>
            {description && (
              <p className="mt-2 text-sm text-zinc-400">{description}</p>
            )}
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {criteria.map((criterion) => (
                <div key={criterion.id} className="rounded border border-zinc-700 p-3">
                  <div className="mb-2 flex items-start justify-between">
                    <div>
                      <h4 className="font-medium text-zinc-50">{criterion.name}</h4>
                      <p className="text-sm text-zinc-400">{criterion.description}</p>
                    </div>
                    <span className="text-sm text-zinc-500">{criterion.weight}%</span>
                  </div>
                  <div className="flex gap-2">
                    {Object.entries(criterion.scale.labels || {}).map(([value, label]) => (
                      <div
                        key={value}
                        className="flex-1 rounded border border-zinc-600 bg-zinc-800 px-2 py-1 text-center text-sm"
                      >
                        <div className="font-medium text-zinc-300">{value}</div>
                        <div className="text-xs text-zinc-500">{label}</div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      ) : (
        <>
          <Card>
            <CardContent className="space-y-4 pt-6">
              <div>
                <label className="mb-1 block text-sm font-medium text-zinc-300">
                  Rubric Name *
                </label>
                <Input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g., Ad Copy Quality"
                />
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-zinc-300">
                  Description
                </label>
                <Textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Describe the purpose of this rubric"
                  rows={3}
                />
              </div>
            </CardContent>
          </Card>

          <div>
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-zinc-50">
                Criteria
                {totalWeight !== 100 && (
                  <span className="ml-2 text-sm text-yellow-500">
                    (Total weight: {totalWeight}% - must equal 100%)
                  </span>
                )}
              </h3>
              <Button onClick={handleAddCriterion} size="sm">
                Add Criterion
              </Button>
            </div>

            <div className="space-y-3">
              {criteria.length === 0 ? (
                <div className="rounded-lg border border-dashed border-zinc-700 p-8 text-center text-zinc-500">
                  No criteria yet. Click "Add Criterion" to get started.
                </div>
              ) : (
                criteria.map((criterion, index) => (
                  <CriteriaBuilder
                    key={criterion.id}
                    criterion={criterion}
                    onChange={(updated) => handleCriterionChange(index, updated)}
                    onDelete={() => handleCriterionDelete(index)}
                  />
                ))
              )}
            </div>
          </div>
        </>
      )}

      <div className="flex justify-end gap-2">
        <Button variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
        <Button onClick={handleSave} disabled={!isValid}>
          {rubric ? 'Update Rubric' : 'Create Rubric'}
        </Button>
      </div>
    </div>
  );
}
