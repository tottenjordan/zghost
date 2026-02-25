export interface RubricCriterion {
  id: string;
  name: string;
  description: string;
  weight: number;
  minScore: number;
  maxScore: number;
}

export interface Rubric {
  id: string;
  name: string;
  description?: string;
  criteria: RubricCriterion[];
}

export interface Rating {
  criterionId: string;
  score: number;
  comment?: string;
}

export interface ArtifactRating {
  artifactId: string;
  rubricId: string;
  ratings: Rating[];
  overallScore?: number;
  ratedBy?: string;
  ratedAt?: string;
}
