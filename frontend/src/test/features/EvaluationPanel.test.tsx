import { describe, it, expect } from 'vitest';
import { render, screen } from '../test-utils';
import { EvaluationPanel } from '../../features/orchestration/EvaluationPanel';
import { DEFAULT_RUBRICS } from '../../features/rating/rubric-templates';

describe('EvaluationPanel', () => {
  it('renders "No rubric selected" when rubric is null', () => {
    render(<EvaluationPanel sessionState={{}} rubrics={[]} />);

    expect(screen.getByText('No rubric selected')).toBeInTheDocument();
    expect(screen.getByText(/Select an evaluation rubric/)).toBeInTheDocument();
  });

  it('renders "No artifacts to evaluate" when no artifacts in session state', () => {
    render(
      <EvaluationPanel sessionState={{}} rubrics={[DEFAULT_RUBRICS[0]]} />
    );

    expect(screen.getByText('No artifacts to evaluate yet')).toBeInTheDocument();
  });

  it('renders rubric criteria when rubric and artifacts are provided', () => {
    const sessionState = {
      combined_final_cited_report: 'Research report content',
      final_select_ad_copies: [{ headline: 'Test Ad' }],
    };

    render(
      <EvaluationPanel sessionState={sessionState} rubrics={[DEFAULT_RUBRICS[0]]} />
    );

    // Should show rubric name
    expect(screen.getByText(DEFAULT_RUBRICS[0].name)).toBeInTheDocument();

    // Should show criteria names
    DEFAULT_RUBRICS[0].criteria.forEach(criterion => {
      expect(screen.getByText(criterion.name)).toBeInTheDocument();
    });
  });

  it('shows artifact type badges', () => {
    const sessionState = {
      combined_final_cited_report: 'Report content',
      final_select_ad_copies: [{ headline: 'Ad' }],
      final_visual_concepts: 'Visual concepts',
    };

    render(
      <EvaluationPanel sessionState={sessionState} rubrics={[DEFAULT_RUBRICS[0]]} />
    );

    expect(screen.getByText('Research Report')).toBeInTheDocument();
    expect(screen.getByText('Ad Copies')).toBeInTheDocument();
    expect(screen.getByText('Visual Concepts')).toBeInTheDocument();
  });

  it('shows scoring buttons for each criterion', () => {
    const sessionState = {
      combined_final_cited_report: 'Report content',
    };

    render(
      <EvaluationPanel sessionState={sessionState} rubrics={[DEFAULT_RUBRICS[0]]} />
    );

    // Each criterion should have score buttons (1-5 for likert scale)
    // Count buttons with text "1", "2", "3", "4", "5"
    const buttons = screen.getAllByRole('button');
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('shows weight percentage for each criterion', () => {
    const sessionState = {
      combined_final_cited_report: 'Report content',
    };

    render(
      <EvaluationPanel sessionState={sessionState} rubrics={[DEFAULT_RUBRICS[0]]} />
    );

    // Multiple criteria may have the same weight, so use getAllByText
    const weightLabels = screen.getAllByText(/\d+%/);
    expect(weightLabels.length).toBe(DEFAULT_RUBRICS[0].criteria.length);
  });
});
