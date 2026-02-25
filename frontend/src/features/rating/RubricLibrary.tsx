import { useState } from 'react';
import { Button } from '../../components/ui/Button';
import { Card, CardContent } from '../../components/ui/Card';
import { Modal } from '../../components/ui/Modal';
import { DEFAULT_RUBRICS, type ExtendedRubric } from './rubric-templates';

interface RubricLibraryProps {
  rubrics: ExtendedRubric[];
  onEdit: (rubric: ExtendedRubric) => void;
  onClone: (id: string) => void;
  onDelete: (id: string) => void;
  onCreate: () => void;
  onCreateFromTemplate: (template: ExtendedRubric) => void;
}

export function RubricLibrary({
  rubrics,
  onEdit,
  onClone,
  onDelete,
  onCreate,
  onCreateFromTemplate,
}: RubricLibraryProps) {
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [showTemplates, setShowTemplates] = useState(false);

  const formatDate = () => {
    // Since we don't have lastModified in the type, show creation indicator
    return 'Custom rubric';
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-zinc-50">Rubric Library</h2>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => setShowTemplates(true)}>
            From Template
          </Button>
          <Button onClick={onCreate}>Create New</Button>
        </div>
      </div>

      {rubrics.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="mb-4 text-zinc-400">No rubrics yet.</p>
            <div className="flex justify-center gap-2">
              <Button onClick={() => setShowTemplates(true)}>
                Start from Template
              </Button>
              <Button variant="secondary" onClick={onCreate}>
                Create from Scratch
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {rubrics.map((rubric) => (
            <Card key={rubric.id}>
              <CardContent className="flex items-center justify-between py-4">
                <div className="flex-1">
                  <h3 className="font-semibold text-zinc-50">{rubric.name}</h3>
                  <p className="text-sm text-zinc-400">
                    {rubric.criteria.length} criteria · {formatDate()}
                  </p>
                  {rubric.description && (
                    <p className="mt-1 text-sm text-zinc-500">{rubric.description}</p>
                  )}
                </div>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => onEdit(rubric)}
                  >
                    Edit
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => onClone(rubric.id)}
                  >
                    Clone
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => setDeleteConfirm(rubric.id)}
                  >
                    Delete
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={deleteConfirm !== null}
        onClose={() => setDeleteConfirm(null)}
        title="Delete Rubric"
      >
        <p className="mb-4 text-zinc-300">
          Are you sure you want to delete this rubric? This action cannot be undone.
        </p>
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={() => setDeleteConfirm(null)}>
            Cancel
          </Button>
          <Button
            variant="danger"
            onClick={() => {
              if (deleteConfirm) {
                onDelete(deleteConfirm);
                setDeleteConfirm(null);
              }
            }}
          >
            Delete
          </Button>
        </div>
      </Modal>

      {/* Templates Modal */}
      <Modal
        isOpen={showTemplates}
        onClose={() => setShowTemplates(false)}
        title="Choose a Template"
        className="max-w-2xl"
      >
        <div className="space-y-3">
          {DEFAULT_RUBRICS.map((template) => (
            <div
              key={template.id}
              className="rounded-lg border border-zinc-700 p-4 hover:border-zinc-600"
            >
              <div className="mb-2 flex items-start justify-between">
                <div>
                  <h3 className="font-semibold text-zinc-50">{template.name}</h3>
                  <p className="text-sm text-zinc-400">{template.description}</p>
                  <p className="mt-1 text-xs text-zinc-500">
                    {template.criteria.length} criteria
                  </p>
                </div>
                <Button
                  size="sm"
                  onClick={() => {
                    onCreateFromTemplate(template);
                    setShowTemplates(false);
                  }}
                >
                  Use Template
                </Button>
              </div>
              <div className="mt-2 flex flex-wrap gap-1">
                {template.criteria.slice(0, 5).map((criterion) => (
                  <span
                    key={criterion.id}
                    className="rounded bg-zinc-800 px-2 py-1 text-xs text-zinc-300"
                  >
                    {criterion.name}
                  </span>
                ))}
                {template.criteria.length > 5 && (
                  <span className="rounded bg-zinc-800 px-2 py-1 text-xs text-zinc-500">
                    +{template.criteria.length - 5} more
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </Modal>
    </div>
  );
}
