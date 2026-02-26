import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '../test-utils';
import userEvent from '@testing-library/user-event';

// Mock the navigate function
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...(actual as object),
    useNavigate: () => mockNavigate,
  };
});

// Mock useCampaignStore while preserving CampaignStoreProvider
const mockStoreState = {
  config: { brand: '', target_product: '', target_audience: '', key_selling_points: '' },
  selectedSearchTrends: [] as any[],
  selectedYtTrends: [] as any[],
  activeRubrics: [] as any[],
  setCampaignConfig: vi.fn(),
  setSelectedTrends: vi.fn(),
  toggleActiveRubric: vi.fn(),
  setAutoStart: vi.fn(),
  isReadyToLaunch: vi.fn(() => ({ ready: false, missing: ['Brand or Product', 'At least 1 trend'] })),
};

vi.mock('../../stores/campaignStore', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...(actual as object),
    useCampaignStore: () => mockStoreState,
  };
});

vi.mock('../../hooks/useSession', () => ({
  useSession: () => ({ session: null, createSession: vi.fn(), loadSession: vi.fn() }),
}));

vi.mock('../../services/trendsCache', () => ({
  fetchLiveTrends: vi.fn(() => Promise.resolve({ searchTrends: [], ytTrends: [] })),
  getCachedTrends: vi.fn(() => null),
  autoSelectFromAvailable: vi.fn(),
}));

vi.mock('./useTrends', () => ({
  useTrends: () => ({
    toggleSearchTrend: vi.fn(),
    toggleYtTrend: vi.fn(),
    clearSelections: vi.fn(),
  }),
}));

const { TrendsPage } = await import('../../features/trends/TrendsPage');

describe('ConfigWizard (TrendsPage)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    // Reset mock store state
    mockStoreState.config = { brand: '', target_product: '', target_audience: '', key_selling_points: '' };
    mockStoreState.selectedSearchTrends = [];
    mockStoreState.selectedYtTrends = [];
    mockStoreState.activeRubrics = [];
    mockStoreState.isReadyToLaunch.mockReturnValue({ ready: false, missing: ['Brand or Product', 'At least 1 trend'] });
  });

  it('renders 4 tabs: Campaign, Trends, Evaluation, Review', () => {
    render(<TrendsPage />);

    expect(screen.getByText('Campaign')).toBeInTheDocument();
    expect(screen.getByText('Trends')).toBeInTheDocument();
    expect(screen.getByText('Evaluation')).toBeInTheDocument();
    expect(screen.getByText('Review')).toBeInTheDocument();
  });

  it('shows page title as "Configure"', () => {
    render(<TrendsPage />);

    expect(screen.getByText('Configure')).toBeInTheDocument();
  });

  it('shows step progress indicator', () => {
    render(<TrendsPage />);

    expect(screen.getByText(/Step 1 of 4/)).toBeInTheDocument();
  });

  it('shows step number badges for each tab', () => {
    render(<TrendsPage />);

    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('4')).toBeInTheDocument();
  });

  it('Review tab shows "Add execution run to orchestrator" button', async () => {
    const user = userEvent.setup();
    render(<TrendsPage />);

    await user.click(screen.getByText('Review'));

    expect(screen.getByText('Add Execution Run to Orchestrator')).toBeInTheDocument();
  });

  it('Review tab launch button is disabled when config is incomplete', async () => {
    const user = userEvent.setup();
    render(<TrendsPage />);

    await user.click(screen.getByText('Review'));

    const launchButton = screen.getByText('Add Execution Run to Orchestrator');
    expect(launchButton.closest('button')).toBeDisabled();
  });

  it('Review tab shows missing items when not ready', async () => {
    const user = userEvent.setup();
    render(<TrendsPage />);

    await user.click(screen.getByText('Review'));

    expect(screen.getByText(/Missing: Brand or Product/)).toBeInTheDocument();
    expect(screen.getByText(/Missing: At least 1 trend/)).toBeInTheDocument();
  });

  it('Review tab launch button navigates to /orchestration when clicked and ready', async () => {
    mockStoreState.isReadyToLaunch.mockReturnValue({ ready: true, missing: [] });
    mockStoreState.config = { brand: 'Google', target_product: 'Pixel', target_audience: '', key_selling_points: '' };

    const user = userEvent.setup();
    render(<TrendsPage />);

    await user.click(screen.getByText('Review'));

    const launchButton = screen.getByText('Add Execution Run to Orchestrator');
    expect(launchButton.closest('button')).not.toBeDisabled();

    await user.click(launchButton);
    expect(mockNavigate).toHaveBeenCalledWith('/orchestration');
  });

  it('tab switching works between tabs', async () => {
    const user = userEvent.setup();
    render(<TrendsPage />);

    // Switch to Evaluation
    await user.click(screen.getByText('Evaluation'));
    expect(screen.getByText('Rubric Library')).toBeInTheDocument();

    // Switch to Review
    await user.click(screen.getByText('Review'));
    expect(screen.getByText('Campaign Summary')).toBeInTheDocument();
  });

  it('shows step indicators', () => {
    render(<TrendsPage />);

    // Step indicators should exist (rounded-full elements)
    const stepIndicators = document.querySelectorAll('.rounded-full');
    expect(stepIndicators.length).toBeGreaterThan(0);
  });
});
