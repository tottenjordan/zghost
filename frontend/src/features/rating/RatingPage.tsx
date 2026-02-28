import { useState, useEffect } from 'react';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../components/ui/Tabs';
import { RaterView } from './RaterView';
import { RubricLibrary } from './RubricLibrary';
import { RubricEditor } from './RubricEditor';
import { RatingSummary } from './RatingSummary';
import { FocusGroupResults } from './FocusGroupResults';
import { useRating } from './useRating';
import { useCampaignStore } from '../../stores/campaignStore';
import { api } from '../../services/api';
import { cn } from '../../lib/utils';
import { ChevronDown } from 'lucide-react';
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

  const { activeRubrics, toggleActiveRubric, sessions, sessionId: activeSessionId } = useCampaignStore();

  const [selectedSessionId, setSelectedSessionId] = useState<string>(activeSessionId || '');
  const [sessionState, setSessionState] = useState<Record<string, any>>({});
  const [editorMode, setEditorMode] = useState<EditorMode>('library');
  const [editingRubric, setEditingRubric] = useState<ExtendedRubric | undefined>();

  // Load session state when run is selected
  useEffect(() => {
    if (!selectedSessionId) return;
    api.getSessionState(selectedSessionId)
      .then((result: any) => setSessionState(result.state || result || {}))
      .catch(() => setSessionState({}));
  }, [selectedSessionId]);

  // Auto-activate rubric when there's only one
  useEffect(() => {
    if (rubrics.length === 1 && activeRubrics.length === 0) {
      toggleActiveRubric(rubrics[0]);
    }
  }, [rubrics, activeRubrics, toggleActiveRubric]);

  const handleCreateRubric = (rubric: Omit<ExtendedRubric, 'id'>) => {
    const created = createRubric(rubric);
    setEditorMode('library');
    // Auto-activate newly created rubric if none is active
    if (activeRubrics.length === 0) {
      toggleActiveRubric(created);
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

  // Voice action listener for scoring
  useEffect(() => {
    const handler = (e: Event) => {
      const { action, params } = (e as CustomEvent).detail;
      if (action === 'score_criterion' && params?.criterion_name && params?.score) {
        // Find the criterion in active rubrics
        for (const rubric of activeRubrics) {
          const criterion = rubric.criteria.find(c =>
            c.name.toLowerCase() === params.criterion_name.toLowerCase()
          );
          if (criterion) {
            submitRating({
              artifactId: 'voice-rated-' + Date.now(),
              rubricId: rubric.id,
              ratings: { [criterion.id]: params.score },
              overallScore: params.score,
              ratedBy: 'Voice Assistant',
            });
            break;
          }
        }
      }
    };
    window.addEventListener('voice-action', handler);
    return () => window.removeEventListener('voice-action', handler);
  }, [activeRubrics, submitRating]);

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="mb-2 text-2xl font-bold text-zinc-50">Rating & Evaluation</h1>
          <p className="text-zinc-400">
            Configure rubrics and evaluate generated artifacts against custom criteria
          </p>
        </div>

        {/* Run selector */}
        {sessions.length > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-zinc-500">Run:</span>
            <div className="relative">
              <select
                value={selectedSessionId}
                onChange={(e) => setSelectedSessionId(e.target.value)}
                className={cn(
                  'appearance-none pl-3 pr-8 py-1.5 rounded-lg border text-xs',
                  'bg-zinc-900 border-zinc-700 text-zinc-300',
                  'focus:outline-none focus:ring-1 focus:ring-blue-500'
                )}
              >
                <option value="" disabled>Select a run...</option>
                {sessions.map((s) => (
                  <option key={s.sessionId} value={s.sessionId}>
                    {s.label} — {s.config?.brand || 'No brand'} ({s.status})
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3 h-3 text-zinc-500 pointer-events-none" />
            </div>
          </div>
        )}
      </div>

      {/* Active rubric banner */}
      <div className="flex items-center gap-3 rounded-lg border border-zinc-800 bg-zinc-900 px-4 py-3">
        <span className="text-sm text-zinc-500">Pipeline rubrics:</span>
        {activeRubrics.length > 0 ? (
          <div className="flex items-center gap-2 flex-wrap">
            {activeRubrics.map((r) => (
              <span key={r.id} className="rounded-full bg-green-900/50 px-2.5 py-0.5 text-xs font-medium text-green-400 border border-green-700">
                {r.name} ({r.criteria.length})
              </span>
            ))}
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
                activeRubricIds={activeRubrics.map(r => r.id)}
                onToggleActive={toggleActiveRubric}
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
          <div className="mt-4 space-y-6">
            {/* Focus Group Results */}
            {selectedSessionId && (
              <FocusGroupResults sessionId={selectedSessionId} />
            )}

            {/* Manual Rating Results */}
            <RatingSummary ratings={ratings} rubrics={rubrics} />
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
