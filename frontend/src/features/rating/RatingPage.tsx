import { useState, useEffect } from 'react';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../components/ui/Tabs';
import { RaterView } from './RaterView';
import { RubricLibrary } from './RubricLibrary';
import { RubricEditor } from './RubricEditor';
import { RatingSummary } from './RatingSummary';
import { useRating } from './useRating';
import { useCampaignStore } from '../../stores/campaignStore';
import type { ExtendedRubric } from './rubric-templates';

type EditorMode = 'library' | 'create' | 'edit';

export function RatingPage() {
  const {
    rubrics,
    ratings,
    createRubric,
    updateRubric,
    deleteRubric,
    cloneRubric,
    submitRating,
  } = useRating();

  const { activeRubric, setActiveRubric } = useCampaignStore();

  const [editorMode, setEditorMode] = useState<EditorMode>('library');
  const [editingRubric, setEditingRubric] = useState<ExtendedRubric | undefined>();

  // Auto-activate rubric when there's only one
  useEffect(() => {
    if (rubrics.length === 1 && !activeRubric) {
      setActiveRubric(rubrics[0]);
    }
  }, [rubrics, activeRubric, setActiveRubric]);

  const handleCreateRubric = (rubric: Omit<ExtendedRubric, 'id'>) => {
    const created = createRubric(rubric);
    setEditorMode('library');
    // Auto-activate newly created rubric if none is active
    if (!activeRubric) {
      setActiveRubric(created);
    }
  };

  const handleUpdateRubric = (rubric: Omit<ExtendedRubric, 'id'>) => {
    if (editingRubric) {
      updateRubric(editingRubric.id, rubric);
      setEditorMode('library');
      setEditingRubric(undefined);
    }
  };

  const handleEdit = (rubric: ExtendedRubric) => {
    setEditingRubric(rubric);
    setEditorMode('edit');
  };

  const handleCreateFromTemplate = (template: ExtendedRubric) => {
    createRubric({
      name: template.name,
      description: template.description,
      criteria: template.criteria,
    });
  };

  const handleCancel = () => {
    setEditorMode('library');
    setEditingRubric(undefined);
  };

  const handleSubmitRating = (rating: any) => {
    submitRating({
      artifactId: 'mock-artifact-' + Date.now(),
      rubricId: rating.rubricId,
      ratings: rating.ratings,
      overallScore: rating.overallScore,
      ratedBy: 'Current User',
    });
  };

  return (
    <div className="space-y-4">
      <div>
        <h1 className="mb-2 text-2xl font-bold text-zinc-50">Rating & Evaluation</h1>
        <p className="text-zinc-400">
          Configure rubrics and evaluate generated artifacts against custom criteria
        </p>
      </div>

      {/* Active rubric banner */}
      <div className="flex items-center gap-3 rounded-lg border border-zinc-800 bg-zinc-900 px-4 py-3">
        <span className="text-sm text-zinc-500">Pipeline rubric:</span>
        {activeRubric ? (
          <div className="flex items-center gap-2">
            <span className="rounded-full bg-green-900/50 px-2.5 py-0.5 text-xs font-medium text-green-400 border border-green-700">
              {activeRubric.name}
            </span>
            <span className="text-xs text-zinc-500">
              {activeRubric.criteria.length} criteria
            </span>
            <button
              onClick={() => setActiveRubric(null)}
              className="ml-2 text-xs text-zinc-500 hover:text-zinc-300"
            >
              Clear
            </button>
          </div>
        ) : (
          <span className="text-xs text-amber-400">
            No rubric selected — create or select one below
          </span>
        )}
      </div>

      <Tabs defaultValue="rate">
        <TabsList>
          <TabsTrigger value="rate">Rate Content</TabsTrigger>
          <TabsTrigger value="rubrics">Manage Rubrics</TabsTrigger>
          <TabsTrigger value="results">Results</TabsTrigger>
        </TabsList>

        <TabsContent value="rate">
          <div className="mt-4">
            {rubrics.length === 0 ? (
              <div className="rounded-lg border border-zinc-700 bg-zinc-800 p-12 text-center">
                <p className="mb-4 text-zinc-400">
                  No rubrics available. Create a rubric first to start rating content.
                </p>
              </div>
            ) : (
              <RaterView rubrics={rubrics} onSubmit={handleSubmitRating} />
            )}
          </div>
        </TabsContent>

        <TabsContent value="rubrics">
          <div className="mt-4">
            {editorMode === 'library' ? (
              <RubricLibrary
                rubrics={rubrics}
                onEdit={handleEdit}
                onClone={cloneRubric}
                onDelete={deleteRubric}
                onCreate={() => setEditorMode('create')}
                onCreateFromTemplate={handleCreateFromTemplate}
                activeRubricId={activeRubric?.id}
                onSetActive={setActiveRubric}
              />
            ) : (
              <RubricEditor
                rubric={editingRubric}
                onSave={editorMode === 'edit' ? handleUpdateRubric : handleCreateRubric}
                onCancel={handleCancel}
              />
            )}
          </div>
        </TabsContent>

        <TabsContent value="results">
          <div className="mt-4">
            <RatingSummary ratings={ratings} rubrics={rubrics} />
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
