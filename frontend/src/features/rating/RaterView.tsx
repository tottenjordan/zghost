import { useState, useEffect } from 'react';
import { Button } from '../../components/ui/Button';
import { Textarea } from '../../components/ui/Textarea';
import { ContentViewer } from './ContentViewer';
import { RatingControls } from './RatingControls';
import type { ExtendedRubric } from './rubric-templates';
import type { Rating } from '../../types/rating';

interface RaterViewProps {
  rubrics: ExtendedRubric[];
  onSubmit: (rating: {
    rubricId: string;
    ratings: Rating[];
    overallScore: number;
    overallComment?: string;
  }) => void;
}

// Mock content for demonstration
const MOCK_CONTENT = {
  ad_copy: {
    type: 'ad_copy' as const,
    data: {
      text: `**Pixel 9: AI-Powered Photography Perfection**\n\nCapture life's moments like never before with Google Pixel 9. Our cutting-edge AI technology ensures every photo is a masterpiece.\n\n✨ Best Take: Never miss the perfect smile\n📸 Magic Eraser: Remove unwanted objects effortlessly\n🌙 Night Sight: Stunning photos even in low light\n\nUpgrade to brilliance. Get Pixel 9 today.`,
    },
  },
  visual_concept: {
    type: 'visual_concept' as const,
    data: {
      url: 'https://via.placeholder.com/800x600/1a1a1a/ffffff?text=Visual+Concept+Preview',
    },
  },
  commercial: {
    type: 'commercial' as const,
    data: {
      url: '',
      scenes: [
        { startTime: 0, endTime: 5, description: 'Product hero shot' },
        { startTime: 5, endTime: 15, description: 'Feature demonstration' },
        { startTime: 15, endTime: 25, description: 'Lifestyle integration' },
        { startTime: 25, endTime: 30, description: 'Call to action' },
      ],
    },
  },
  report: {
    type: 'report' as const,
    data: {
      text: `**Market Research Report: Smartphone Photography Trends 2026**\n\n**Executive Summary**\n\nConsumer demand for advanced smartphone photography capabilities continues to grow, with AI-powered features becoming a primary purchase consideration.\n\n**Key Findings**\n\n1. 78% of consumers prioritize camera quality when selecting smartphones\n2. AI photo editing features increase purchase intent by 45%\n3. Social media sharing drives demand for instant photo enhancement\n\n**Recommendations**\n\n• Emphasize AI capabilities in marketing messaging\n• Demonstrate real-world use cases\n• Highlight ease of use for non-professional photographers`,
    },
  },
};

export function RaterView({ rubrics, onSubmit }: RaterViewProps) {
  const [selectedRubricId, setSelectedRubricId] = useState<string>('');
  const [contentType, setContentType] = useState<'ad_copy' | 'visual_concept' | 'commercial' | 'report'>('ad_copy');
  const [ratings, setRatings] = useState<Map<string, { score: number; comment?: string }>>(new Map());
  const [overallComment, setOverallComment] = useState('');

  const selectedRubric = rubrics.find((r) => r.id === selectedRubricId);

  useEffect(() => {
    // Reset ratings when rubric changes
    setRatings(new Map());
    setOverallComment('');
  }, [selectedRubricId]);

  const handleRatingChange = (criterionId: string, score: number) => {
    const current = ratings.get(criterionId) || {};
    setRatings(new Map(ratings.set(criterionId, { ...current, score })));
  };

  const handleCommentChange = (criterionId: string, comment: string) => {
    const current = ratings.get(criterionId) || { score: 0 };
    setRatings(new Map(ratings.set(criterionId, { ...current, comment })));
  };

  const calculateOverallScore = (): number => {
    if (!selectedRubric) return 0;

    let totalWeightedScore = 0;
    let totalWeight = 0;

    selectedRubric.criteria.forEach((criterion) => {
      const rating = ratings.get(criterion.id);
      if (rating?.score !== undefined) {
        const normalized = (rating.score - criterion.scale.min) / (criterion.scale.max - criterion.scale.min);
        totalWeightedScore += normalized * criterion.weight;
        totalWeight += criterion.weight;
      }
    });

    return totalWeight > 0 ? (totalWeightedScore / totalWeight) * 100 : 0;
  };

  const handleSubmit = () => {
    if (!selectedRubric) return;

    const ratingsList: Rating[] = Array.from(ratings.entries()).map(
      ([criterionId, { score, comment }]) => ({
        criterionId,
        score,
        comment,
      })
    );

    onSubmit({
      rubricId: selectedRubricId,
      ratings: ratingsList,
      overallScore: calculateOverallScore(),
      overallComment: overallComment || undefined,
    });

    // Reset form
    setRatings(new Map());
    setOverallComment('');
  };

  const isComplete = selectedRubric?.criteria.every((c) => ratings.has(c.id) && ratings.get(c.id)?.score !== undefined);
  const overallScore = calculateOverallScore();

  return (
    <div className="space-y-4">
      <div className="flex gap-4">
        <div className="flex-1">
          <label className="mb-1 block text-sm font-medium text-zinc-300">
            Select Rubric
          </label>
          <select
            value={selectedRubricId}
            onChange={(e) => setSelectedRubricId(e.target.value)}
            className="flex h-10 w-full rounded-md border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
          >
            <option value="">Choose a rubric...</option>
            {rubrics.map((rubric) => (
              <option key={rubric.id} value={rubric.id}>
                {rubric.name} ({rubric.criteria.length} criteria)
              </option>
            ))}
          </select>
        </div>

        <div className="flex-1">
          <label className="mb-1 block text-sm font-medium text-zinc-300">
            Content Type
          </label>
          <select
            value={contentType}
            onChange={(e) => setContentType(e.target.value as any)}
            className="flex h-10 w-full rounded-md border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
          >
            <option value="ad_copy">Ad Copy</option>
            <option value="visual_concept">Visual Concept</option>
            <option value="commercial">Commercial</option>
            <option value="report">Research Report</option>
          </select>
        </div>
      </div>

      {!selectedRubric ? (
        <div className="rounded-lg border border-zinc-700 bg-zinc-800 p-12 text-center text-zinc-400">
          Select a rubric to begin rating
        </div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {/* Left Panel: Content */}
          <div>
            <h3 className="mb-3 text-lg font-semibold text-zinc-50">Content</h3>
            <ContentViewer content={MOCK_CONTENT[contentType]} />
          </div>

          {/* Right Panel: Rating Form */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-zinc-50">
                {selectedRubric.name}
              </h3>
              {isComplete && (
                <div className="text-right">
                  <div className="text-sm text-zinc-400">Overall Score</div>
                  <div
                    className={`text-2xl font-bold ${
                      overallScore >= 70
                        ? 'text-green-400'
                        : overallScore >= 40
                        ? 'text-yellow-400'
                        : 'text-red-400'
                    }`}
                  >
                    {overallScore.toFixed(0)}%
                  </div>
                </div>
              )}
            </div>

            {selectedRubric.description && (
              <p className="text-sm text-zinc-400">{selectedRubric.description}</p>
            )}

            <div className="space-y-3">
              {selectedRubric.criteria.map((criterion) => (
                <RatingControls
                  key={criterion.id}
                  criterion={criterion}
                  value={ratings.get(criterion.id)?.score}
                  comment={ratings.get(criterion.id)?.comment}
                  onChange={(score) => handleRatingChange(criterion.id, score)}
                  onCommentChange={(comment) => handleCommentChange(criterion.id, comment)}
                />
              ))}
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-zinc-300">
                Overall Comments
              </label>
              <Textarea
                value={overallComment}
                onChange={(e) => setOverallComment(e.target.value)}
                placeholder="Add general comments about this content..."
                rows={3}
              />
            </div>

            <Button
              onClick={handleSubmit}
              disabled={!isComplete}
              className="w-full"
            >
              Submit Rating
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
