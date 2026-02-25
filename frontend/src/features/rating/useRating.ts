import { useState, useEffect } from 'react';
import type { ArtifactRating } from '../../types/rating';
import { DEFAULT_RUBRICS, type ExtendedRubric } from './rubric-templates';

const RUBRICS_STORAGE_KEY = 'rating-rubrics';
const RATINGS_STORAGE_KEY = 'artifact-ratings';

export function useRating() {
  const [rubrics, setRubrics] = useState<ExtendedRubric[]>([]);
  const [ratings, setRatings] = useState<ArtifactRating[]>([]);

  // Load from localStorage on mount
  useEffect(() => {
    const storedRubrics = localStorage.getItem(RUBRICS_STORAGE_KEY);
    if (storedRubrics) {
      setRubrics(JSON.parse(storedRubrics));
    } else {
      // Initialize with default templates
      setRubrics(DEFAULT_RUBRICS);
      localStorage.setItem(RUBRICS_STORAGE_KEY, JSON.stringify(DEFAULT_RUBRICS));
    }

    const storedRatings = localStorage.getItem(RATINGS_STORAGE_KEY);
    if (storedRatings) {
      setRatings(JSON.parse(storedRatings));
    }
  }, []);

  // Rubric CRUD operations
  const createRubric = (rubric: Omit<ExtendedRubric, 'id'>) => {
    const newRubric = {
      ...rubric,
      id: `rubric-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    };
    const updated = [...rubrics, newRubric];
    setRubrics(updated);
    localStorage.setItem(RUBRICS_STORAGE_KEY, JSON.stringify(updated));
    return newRubric;
  };

  const updateRubric = (id: string, updates: Partial<ExtendedRubric>) => {
    const updated = rubrics.map((r) =>
      r.id === id ? { ...r, ...updates } : r
    );
    setRubrics(updated);
    localStorage.setItem(RUBRICS_STORAGE_KEY, JSON.stringify(updated));
  };

  const deleteRubric = (id: string) => {
    const updated = rubrics.filter((r) => r.id !== id);
    setRubrics(updated);
    localStorage.setItem(RUBRICS_STORAGE_KEY, JSON.stringify(updated));
  };

  const cloneRubric = (id: string) => {
    const rubric = rubrics.find((r) => r.id === id);
    if (!rubric) return;

    const clone = {
      ...rubric,
      id: `rubric-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      name: `${rubric.name} (Copy)`,
      criteria: rubric.criteria.map((c) => ({
        ...c,
        id: `criterion-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      })),
    };
    const updated = [...rubrics, clone];
    setRubrics(updated);
    localStorage.setItem(RUBRICS_STORAGE_KEY, JSON.stringify(updated));
    return clone;
  };

  const getRubric = (id: string) => {
    return rubrics.find((r) => r.id === id);
  };

  // Rating operations
  const submitRating = (rating: Omit<ArtifactRating, 'ratedAt'>) => {
    const newRating = {
      ...rating,
      ratedAt: new Date().toISOString(),
    };
    const updated = [...ratings, newRating];
    setRatings(updated);
    localStorage.setItem(RATINGS_STORAGE_KEY, JSON.stringify(updated));
    return newRating;
  };

  const getRatingsForArtifact = (artifactId: string) => {
    return ratings.filter((r) => r.artifactId === artifactId);
  };

  const getRatingsByRubric = (rubricId: string) => {
    return ratings.filter((r) => r.rubricId === rubricId);
  };

  const calculateWeightedScore = (
    rubricId: string,
    criteriaScores: Array<{ criterionId: string; score: number }>
  ): number => {
    const rubric = getRubric(rubricId);
    if (!rubric) return 0;

    let totalWeightedScore = 0;
    let totalWeight = 0;

    criteriaScores.forEach(({ criterionId, score }) => {
      const criterion = rubric.criteria.find((c) => c.id === criterionId);
      if (criterion) {
        const normalizedScore = (score - criterion.scale.min) / (criterion.scale.max - criterion.scale.min);
        totalWeightedScore += normalizedScore * criterion.weight;
        totalWeight += criterion.weight;
      }
    });

    return totalWeight > 0 ? (totalWeightedScore / totalWeight) * 100 : 0;
  };

  const resetToDefaults = () => {
    setRubrics(DEFAULT_RUBRICS);
    localStorage.setItem(RUBRICS_STORAGE_KEY, JSON.stringify(DEFAULT_RUBRICS));
  };

  return {
    rubrics,
    ratings,
    createRubric,
    updateRubric,
    deleteRubric,
    cloneRubric,
    getRubric,
    submitRating,
    getRatingsForArtifact,
    getRatingsByRubric,
    calculateWeightedScore,
    resetToDefaults,
  };
}
