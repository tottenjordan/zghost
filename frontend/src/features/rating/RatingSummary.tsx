import { Button } from '../../components/ui/Button';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import type { ArtifactRating } from '../../types/rating';
import type { ExtendedRubric } from './rubric-templates';

interface RatingSummaryProps {
  ratings: ArtifactRating[];
  rubrics: ExtendedRubric[];
}

export function RatingSummary({ ratings, rubrics }: RatingSummaryProps) {
  const exportAsJSON = () => {
    const dataStr = JSON.stringify(ratings, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `ratings-${new Date().toISOString().split('T')[0]}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  if (ratings.length === 0) {
    return (
      <div className="rounded-lg border border-zinc-700 bg-zinc-800 p-12 text-center text-zinc-400">
        No ratings yet. Rate some content to see results here.
      </div>
    );
  }

  // Group ratings by rubric
  const ratingsByRubric = ratings.reduce((acc, rating) => {
    if (!acc[rating.rubricId]) {
      acc[rating.rubricId] = [];
    }
    acc[rating.rubricId].push(rating);
    return acc;
  }, {} as Record<string, ArtifactRating[]>);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-zinc-50">Rating Results</h2>
        <Button onClick={exportAsJSON} variant="secondary" size="sm">
          Export as JSON
        </Button>
      </div>

      {Object.entries(ratingsByRubric).map(([rubricId, rubricRatings]) => {
        const rubric = rubrics.find((r) => r.id === rubricId);
        if (!rubric) return null;

        // Calculate averages if multiple ratings
        const criterionAverages = new Map<string, { avg: number; count: number; comments: string[] }>();

        rubricRatings.forEach((rating) => {
          rating.ratings.forEach((r) => {
            const current = criterionAverages.get(r.criterionId) || { avg: 0, count: 0, comments: [] };
            criterionAverages.set(r.criterionId, {
              avg: current.avg + r.score,
              count: current.count + 1,
              comments: r.comment ? [...current.comments, r.comment] : current.comments,
            });
          });
        });

        const avgOverallScore =
          rubricRatings.reduce((sum, r) => sum + (r.overallScore || 0), 0) / rubricRatings.length;

        return (
          <Card key={rubricId}>
            <CardHeader>
              <div className="flex items-start justify-between">
                <div>
                  <CardTitle>{rubric.name}</CardTitle>
                  <p className="mt-1 text-sm text-zinc-400">
                    {rubricRatings.length} rating{rubricRatings.length > 1 ? 's' : ''}
                  </p>
                </div>
                <div className="text-right">
                  <div className="text-sm text-zinc-400">Avg. Score</div>
                  <div
                    className={`text-3xl font-bold ${
                      avgOverallScore >= 70
                        ? 'text-green-400'
                        : avgOverallScore >= 40
                        ? 'text-yellow-400'
                        : 'text-red-400'
                    }`}
                  >
                    {avgOverallScore.toFixed(0)}%
                  </div>
                </div>
              </div>
            </CardHeader>

            <CardContent className="space-y-4">
              {/* Per-criterion breakdown */}
              <div className="space-y-3">
                {rubric.criteria.map((criterion) => {
                  const data = criterionAverages.get(criterion.id);
                  if (!data) return null;

                  const avgScore = data.avg / data.count;
                  const normalizedScore =
                    ((avgScore - criterion.scale.min) / (criterion.scale.max - criterion.scale.min)) * 100;

                  return (
                    <div key={criterion.id} className="space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-zinc-300">
                          {criterion.name}
                          <span className="ml-2 text-xs text-zinc-500">({criterion.weight}%)</span>
                        </span>
                        <span className="text-sm text-zinc-400">
                          {avgScore.toFixed(1)} / {criterion.scale.max}
                        </span>
                      </div>
                      <div className="h-2 overflow-hidden rounded-full bg-zinc-800">
                        <div
                          className={`h-full transition-all ${
                            normalizedScore >= 70
                              ? 'bg-green-500'
                              : normalizedScore >= 40
                              ? 'bg-yellow-500'
                              : 'bg-red-500'
                          }`}
                          style={{ width: `${normalizedScore}%` }}
                        />
                      </div>
                      {data.comments.length > 0 && (
                        <div className="mt-1 space-y-1">
                          {data.comments.map((comment, idx) => (
                            <p key={idx} className="text-xs text-zinc-500">
                              "{comment}"
                            </p>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Individual ratings */}
              {rubricRatings.length > 1 && (
                <details className="mt-4">
                  <summary className="cursor-pointer text-sm font-medium text-zinc-400 hover:text-zinc-300">
                    View individual ratings ({rubricRatings.length})
                  </summary>
                  <div className="mt-3 space-y-2">
                    {rubricRatings.map((rating, idx) => (
                      <div
                        key={idx}
                        className="rounded border border-zinc-700 bg-zinc-900 p-3 text-sm"
                      >
                        <div className="mb-1 flex items-center justify-between">
                          <span className="text-zinc-400">
                            {rating.ratedBy || 'Anonymous'} •{' '}
                            {rating.ratedAt
                              ? new Date(rating.ratedAt).toLocaleString()
                              : 'Unknown date'}
                          </span>
                          <span className="font-semibold text-zinc-300">
                            {rating.overallScore?.toFixed(0)}%
                          </span>
                        </div>
                        {rating.ratings.filter((r) => r.comment).map((r) => {
                          const criterion = rubric.criteria.find((c) => c.id === r.criterionId);
                          return criterion?.name ? (
                            <p key={r.criterionId} className="text-xs text-zinc-500">
                              <span className="font-medium">{criterion.name}:</span> {r.comment}
                            </p>
                          ) : null;
                        })}
                      </div>
                    ))}
                  </div>
                </details>
              )}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
