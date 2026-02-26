import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '../test-utils';
import userEvent from '@testing-library/user-event';
import { RubricLibrary } from '../../features/rating/RubricLibrary';
import { DEFAULT_RUBRICS, type ExtendedRubric } from '../../features/rating/rubric-templates';

describe('CUJ 3a: Rubric Library & Activation', () => {
  const mockOnEdit = vi.fn();
  const mockOnClone = vi.fn();
  const mockOnDelete = vi.fn();
  const mockOnCreate = vi.fn();
  const mockOnCreateFromTemplate = vi.fn();
  const mockOnSetActive = vi.fn();

  const defaultProps = {
    rubrics: DEFAULT_RUBRICS,
    onEdit: mockOnEdit,
    onClone: mockOnClone,
    onDelete: mockOnDelete,
    onCreate: mockOnCreate,
    onCreateFromTemplate: mockOnCreateFromTemplate,
    onSetActive: mockOnSetActive,
  };

  it('shows rubric library with available rubrics', () => {
    render(<RubricLibrary {...defaultProps} />);

    expect(screen.getByText('Rubric Library')).toBeInTheDocument();
    expect(screen.getByText('Ad Copy Quality')).toBeInTheDocument();
    expect(screen.getByText('Commercial Production')).toBeInTheDocument();
    expect(screen.getByText('Visual Concept')).toBeInTheDocument();
    expect(screen.getByText('Research Report')).toBeInTheDocument();
  });

  it('activates rubric for pipeline when button clicked', async () => {
    const user = userEvent.setup();
    render(<RubricLibrary {...defaultProps} />);

    // All rubrics should have "Activate for Pipeline" button (none are active)
    const activateButtons = screen.getAllByText('Activate for Pipeline');
    expect(activateButtons.length).toBeGreaterThan(0);

    // Click the first one
    await user.click(activateButtons[0]);

    expect(mockOnSetActive).toHaveBeenCalledWith(DEFAULT_RUBRICS[0]);
  });

  it('shows "Active for Pipeline" badge when rubric is active', () => {
    render(
      <RubricLibrary
        {...defaultProps}
        activeRubricId={DEFAULT_RUBRICS[0].id}
      />
    );

    expect(screen.getByText('Active for Pipeline')).toBeInTheDocument();
  });

  it('shows Deactivate button for active rubric', () => {
    render(
      <RubricLibrary
        {...defaultProps}
        activeRubricId={DEFAULT_RUBRICS[0].id}
      />
    );

    expect(screen.getByText('Deactivate')).toBeInTheDocument();
  });

  it('allows deactivating an active rubric', async () => {
    const user = userEvent.setup();
    render(
      <RubricLibrary
        {...defaultProps}
        activeRubricId={DEFAULT_RUBRICS[0].id}
      />
    );

    await user.click(screen.getByText('Deactivate'));
    expect(mockOnSetActive).toHaveBeenCalledWith(null);
  });

  it('shows criteria count for each rubric', () => {
    render(<RubricLibrary {...defaultProps} />);

    // Ad Copy Quality has 5 criteria
    expect(screen.getAllByText(/5 criteria/).length).toBeGreaterThan(0);
  });

  it('shows empty state when no rubrics exist', () => {
    render(<RubricLibrary {...defaultProps} rubrics={[]} />);

    expect(screen.getByText('No rubrics yet.')).toBeInTheDocument();
  });
});
