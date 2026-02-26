import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, within } from '../test-utils';
import userEvent from '@testing-library/user-event';

// Mock useRating hook
const mockUseRating = {
  rubrics: [] as any[],
  ratings: [] as any[],
  createRubric: vi.fn((r: any) => ({ ...r, id: 'new-rubric-1' })),
  updateRubric: vi.fn(),
  deleteRubric: vi.fn(),
  cloneRubric: vi.fn(),
  submitRating: vi.fn(),
};

vi.mock('../../features/rating/useRating', () => ({
  useRating: () => mockUseRating,
}));

// Mock campaign store
const mockStoreState = {
  config: { brand: '', target_product: '', target_audience: '', key_selling_points: '' },
  selectedSearchTrends: [] as any[],
  selectedYtTrends: [] as any[],
  activeRubric: null as any,
  sessions: [] as any[],
  activeSessionIndex: -1,
  sessionId: null as string | null,
  pipelineStatus: 'idle' as string,
  commercialDuration: 30 as 10 | 15 | 30,
  setCampaignConfig: vi.fn(),
  setSelectedTrends: vi.fn(),
  setActiveRubric: vi.fn(),
  setSessionId: vi.fn(),
  setPipelineStatus: vi.fn(),
  addSession: vi.fn(),
  removeSession: vi.fn(),
  setActiveSession: vi.fn(),
  updateSessionStatus: vi.fn(),
  setCommercialDuration: vi.fn(),
  reset: vi.fn(),
  isReadyToLaunch: vi.fn(() => ({ ready: false, missing: [] })),
};

vi.mock('../../stores/campaignStore', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...(actual as object),
    useCampaignStore: () => mockStoreState,
  };
});

const { RatingPage } = await import('../../features/rating/RatingPage');

describe('CUJ 3d: Evaluation Studio', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    mockStoreState.activeRubric = null;
    mockUseRating.rubrics = [
      {
        id: 'ad-copy-quality',
        name: 'Ad Copy Quality',
        description: 'Evaluate ad copy effectiveness',
        criteria: [
          {
            id: 'creativity',
            name: 'Creativity',
            description: 'Originality',
            weight: 20,
            scale: { type: 'likert', min: 1, max: 5, labels: { 1: 'Poor', 5: 'Excellent' } },
          },
          {
            id: 'relevance',
            name: 'Relevance',
            description: 'Relevance to audience',
            weight: 30,
            scale: { type: 'likert', min: 1, max: 5, labels: { 1: 'Irrelevant', 5: 'Targeted' } },
          },
        ],
      },
      {
        id: 'commercial-production',
        name: 'Commercial Production',
        description: 'Evaluate commercial quality',
        criteria: [
          {
            id: 'visual-quality',
            name: 'Visual Quality',
            description: 'Production quality',
            weight: 25,
            scale: { type: 'likert', min: 1, max: 5, labels: { 1: 'Poor', 5: 'Professional' } },
          },
        ],
      },
    ];
    mockUseRating.ratings = [];
  });

  it('renders rating page with Rate, Rubrics, Results tabs', () => {
    render(<RatingPage />);

    expect(screen.getByText('Rating & Evaluation')).toBeInTheDocument();
    expect(screen.getByText('Rate Content')).toBeInTheDocument();
    expect(screen.getByText('Manage Rubrics')).toBeInTheDocument();
    expect(screen.getByText('Results')).toBeInTheDocument();
  });

  it('shows rubric selector in rate view', () => {
    render(<RatingPage />);

    // The RaterView should have the "Choose a rubric..." option
    expect(screen.getByText('Choose a rubric...')).toBeInTheDocument();
  });

  it('shows content type selector with options', () => {
    render(<RatingPage />);

    expect(screen.getByText('Ad Copy')).toBeInTheDocument();
    expect(screen.getByText('Visual Concept')).toBeInTheDocument();
    expect(screen.getByText('Commercial')).toBeInTheDocument();
    expect(screen.getByText('Research Report')).toBeInTheDocument();
  });

  it('shows rubric options in dropdown', () => {
    render(<RatingPage />);

    // Both rubrics should appear as options
    expect(screen.getByText(/Ad Copy Quality \(2 criteria\)/)).toBeInTheDocument();
    expect(screen.getByText(/Commercial Production \(1 criteria\)/)).toBeInTheDocument();
  });

  it('shows "select a rubric" prompt before selection', () => {
    render(<RatingPage />);

    expect(screen.getByText('Select a rubric to begin rating')).toBeInTheDocument();
  });

  it('shows rating criteria after selecting a rubric', async () => {
    const user = userEvent.setup();
    render(<RatingPage />);

    // Select the Ad Copy Quality rubric
    const select = screen.getByDisplayValue('Choose a rubric...');
    await user.selectOptions(select, 'ad-copy-quality');

    expect(screen.getByText('Creativity')).toBeInTheDocument();
    expect(screen.getByText('Relevance')).toBeInTheDocument();
  });

  it('shows submit button disabled until all criteria rated', async () => {
    const user = userEvent.setup();
    render(<RatingPage />);

    const select = screen.getByDisplayValue('Choose a rubric...');
    await user.selectOptions(select, 'ad-copy-quality');

    const submitButton = screen.getByText('Submit Rating');
    expect(submitButton.closest('button')).toBeDisabled();
  });

  it.skip('displays LLM automated scores alongside human scores — NOT IMPLEMENTED', () => {
    // TODO: CUJ 3.4 specifies dual LLM + Human scoring.
    // The RaterView currently only supports human scoring.
    // Implement an LLM auto-score panel that shows automated evaluation results
    // alongside the human rating interface.
  });

  it.skip('persists evaluations to a backend database — NOT IMPLEMENTED, uses localStorage', () => {
    // TODO: CUJ 3.4 specifies persisting evaluations to a database.
    // Currently useRating stores ratings in localStorage only.
    // Implement API endpoints and database storage for evaluation persistence.
  });
});
