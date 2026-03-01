import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { CheckCircle, XCircle, TrendingUp } from 'lucide-react';
import type { ExtendedRubric } from './rubric-templates';

interface EvalCase {
  query: string;
  expected_response: string;
  actual_response: string;
  scores: Record<string, number>;
  pass: boolean;
}

interface EvalResultsViewProps {
  evalId: string;
  results: {
    cases: EvalCase[];
    overall_pass: boolean;
    overall_score: number;
  };
  activeRubric?: ExtendedRubric;
  onApplyToRating?: (scores: Record<string, number>) => void;
  brand?: string;
  targetProduct?: string;
}

export function EvalResultsView({
  evalId,
  results,
  activeRubric,
  onApplyToRating,
  brand,
  targetProduct,
}: EvalResultsViewProps) {
  const { cases, overall_pass, overall_score } = results;

  const handleApplyToRating = () => {
    if (!activeRubric || cases.length === 0) return;

    // Calculate average scores per criterion across all cases
    const avgScores: Record<string, number> = {};
    activeRubric.criteria.forEach(criterion => {
      const scores = cases
        .map(c => c.scores[criterion.name] || 0)
        .filter(s => s > 0);
      avgScores[criterion.name] = scores.length > 0
        ? scores.reduce((a, b) => a + b, 0) / scores.length
        : 0;
    });

    onApplyToRating?.(avgScores);
  };

  return (
    <div className="space-y-6">
      {/* Summary Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              Evaluation Results
              {overall_pass ? (
                <CheckCircle className="h-5 w-5 text-green-500" />
              ) : (
                <XCircle className="h-5 w-5 text-red-500" />
              )}
            </CardTitle>
            {activeRubric && onApplyToRating && (
              <Button
                onClick={handleApplyToRating}
                variant="primary"
                size="sm"
                className="flex items-center gap-1.5"
              >
                <TrendingUp className="h-4 w-4" />
                Apply to Rating
              </Button>
            )}
          </div>
          <p className="text-xs text-zinc-500">
            Eval ID: {evalId}
            {brand && <span className="ml-2 text-zinc-400">| {brand}{targetProduct ? ` — ${targetProduct}` : ''}</span>}
          </p>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <p className="text-sm font-medium text-zinc-400">Total Cases</p>
              <p className="text-2xl font-bold text-zinc-100">{cases.length}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-zinc-400">Passed</p>
              <p className="text-2xl font-bold text-green-400">
                {cases.filter(c => c.pass).length}
              </p>
            </div>
            <div>
              <p className="text-sm font-medium text-zinc-400">Overall Score</p>
              <p className="text-2xl font-bold text-blue-400">
                {(overall_score * 100).toFixed(1)}%
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Results Table */}
      <Card>
        <CardHeader>
          <CardTitle>Test Cases</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-800">
                  <th className="pb-2 text-left font-medium text-zinc-400">Status</th>
                  <th className="pb-2 text-left font-medium text-zinc-400">Query</th>
                  <th className="pb-2 text-left font-medium text-zinc-400">Expected</th>
                  <th className="pb-2 text-left font-medium text-zinc-400">Actual</th>
                  {activeRubric && (
                    <th className="pb-2 text-left font-medium text-zinc-400">Scores</th>
                  )}
                </tr>
              </thead>
              <tbody>
                {cases.map((testCase, idx) => (
                  <tr key={idx} className="border-b border-zinc-800/50">
                    <td className="py-3">
                      {testCase.pass ? (
                        <Badge variant="default" className="bg-green-600">
                          PASS
                        </Badge>
                      ) : (
                        <Badge variant="default" className="bg-red-600">
                          FAIL
                        </Badge>
                      )}
                    </td>
                    <td className="py-3 text-zinc-300 max-w-xs truncate">
                      {testCase.query}
                    </td>
                    <td className="py-3 text-zinc-400 max-w-xs truncate">
                      {testCase.expected_response}
                    </td>
                    <td className="py-3 text-zinc-300 max-w-xs truncate">
                      {testCase.actual_response}
                    </td>
                    {activeRubric && (
                      <td className="py-3">
                        <div className="flex flex-col gap-1">
                          {activeRubric.criteria.map(criterion => {
                            const score = testCase.scores[criterion.name];
                            return score !== undefined ? (
                              <div key={criterion.name} className="text-xs">
                                <span className="text-zinc-400">{criterion.name}:</span>{' '}
                                <span className="text-zinc-200 font-medium">
                                  {score.toFixed(1)}
                                </span>
                              </div>
                            ) : null;
                          })}
                        </div>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
