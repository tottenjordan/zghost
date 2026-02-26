import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '../test-utils';
import userEvent from '@testing-library/user-event';

// Mock navigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...(actual as object),
    useNavigate: () => mockNavigate,
  };
});

// Mock campaign store with controllable state
const mockStoreState = {
  config: { brand: '', target_product: '', target_audience: '', key_selling_points: '' },
  selectedSearchTrends: [] as any[],
  selectedYtTrends: [] as any[],
  activeRubric: null as any,
  setCampaignConfig: vi.fn(),
  setSelectedTrends: vi.fn(),
  setActiveRubric: vi.fn(),
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

// Controllable trend fetch mocks
const mockFetchLiveTrends = vi.fn();
const mockGetCachedTrends = vi.fn();

vi.mock('../../services/trendsCache', () => ({
  fetchLiveTrends: (...args: any[]) => mockFetchLiveTrends(...args),
  getCachedTrends: (...args: any[]) => mockGetCachedTrends(...args),
  autoSelectFromAvailable: vi.fn(),
}));

vi.mock('../../features/trends/useTrends', () => ({
  useTrends: () => ({
    toggleSearchTrend: vi.fn(),
    toggleYtTrend: vi.fn(),
    clearSelections: vi.fn(),
  }),
}));

const { TrendsPage } = await import('../../features/trends/TrendsPage');

describe('CUJ 1: Campaign Setup Wizard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    mockStoreState.config = { brand: '', target_product: '', target_audience: '', key_selling_points: '' };
    mockStoreState.selectedSearchTrends = [];
    mockStoreState.selectedYtTrends = [];
    mockStoreState.activeRubric = null;
    mockStoreState.isReadyToLaunch.mockReturnValue({ ready: false, missing: ['Brand or Product', 'At least 1 trend'] });
    // Default: trends fetch is pending, no cache
    mockFetchLiveTrends.mockReturnValue(new Promise(() => {}));
    mockGetCachedTrends.mockReturnValue(null);
  });

  it('shows loading indicator while fetching trends', async () => {
    render(<TrendsPage />);

    await waitFor(() => {
      expect(screen.getByText(/Fetching live trends from backend agents/)).toBeInTheDocument();
    });
  });

  it('does not block UI while fetching trends', async () => {
    render(<TrendsPage />);

    // Campaign tab is the default — form inputs should be interactive even while trends fetch
    expect(screen.getByPlaceholderText('e.g., Google Pixel')).toBeEnabled();
    expect(screen.getByPlaceholderText('e.g., Pixel 9 Pro')).toBeEnabled();
    expect(screen.getByPlaceholderText('e.g., Tech-savvy millennials')).toBeEnabled();
  });

  it('captures all campaign config inputs and saves them', async () => {
    const user = userEvent.setup();
    render(<TrendsPage />);

    await user.type(screen.getByPlaceholderText('e.g., Google Pixel'), 'TestBrand');
    await user.type(screen.getByPlaceholderText('e.g., Pixel 9 Pro'), 'TestProduct');
    await user.type(screen.getByPlaceholderText('e.g., Tech-savvy millennials'), 'TestAudience');
    await user.type(screen.getByPlaceholderText(/AI-powered camera/), 'TestPoints');

    await user.click(screen.getByText('Save Configuration'));

    expect(mockStoreState.setCampaignConfig).toHaveBeenCalledWith({
      brand: 'TestBrand',
      target_product: 'TestProduct',
      target_audience: 'TestAudience',
      key_selling_points: 'TestPoints',
    });
  });

  it('handles PDF drag-and-drop upload', async () => {
    render(<TrendsPage />);

    const dropzoneText = screen.getByText('Drag and drop a PDF file, or click to browse');
    const dropzone = dropzoneText.closest('div[class*="border-dashed"]')!;
    const file = new File(['pdf-content'], 'marketing_guide.pdf', { type: 'application/pdf' });

    fireEvent.drop(dropzone, {
      dataTransfer: { files: [file] },
    });

    await waitFor(() => {
      expect(screen.getByText('marketing_guide.pdf')).toBeInTheDocument();
    });
  });

  it('rejects non-PDF files', () => {
    render(<TrendsPage />);

    const dropzoneText = screen.getByText('Drag and drop a PDF file, or click to browse');
    const dropzone = dropzoneText.closest('div[class*="border-dashed"]')!;
    const file = new File(['text-content'], 'notes.txt', { type: 'text/plain' });

    fireEvent.drop(dropzone, {
      dataTransfer: { files: [file] },
    });

    // Dropzone should still be visible (file was rejected)
    expect(screen.getByText('Drag and drop a PDF file, or click to browse')).toBeInTheDocument();
  });

  it('shows populated trends after fetch completes', async () => {
    const mockTrends = {
      searchTrends: [
        { rank: 1, title: 'AI Photography', relatedQueries: '', formattedTraffic: '100K+', trendDate: '' },
        { rank: 2, title: 'Pixel Camera', relatedQueries: '', formattedTraffic: '50K+', trendDate: '' },
      ],
      ytTrends: [
        { rank: 1, title: 'Best Phone Camera 2026', description: '', channelName: 'TechReview', viewCount: '1M', publishedAt: '' },
      ],
      fetchedAt: Date.now(),
      sessionId: 'test-session',
    };

    mockFetchLiveTrends.mockResolvedValue(mockTrends);
    const user = userEvent.setup();

    render(<TrendsPage />);

    // Wait for trends to load
    await waitFor(() => {
      expect(screen.queryByText(/Fetching live trends/)).not.toBeInTheDocument();
    });

    // Switch to Trends tab
    await user.click(screen.getByText('Trends'));

    await waitFor(() => {
      expect(screen.getByText('AI Photography')).toBeInTheDocument();
    });
  });

  it('shows campaign summary on Review tab', async () => {
    const user = userEvent.setup();
    mockStoreState.config = {
      brand: 'Google Pixel',
      target_product: 'Pixel 9 Pro',
      target_audience: 'Tech-savvy millennials',
      key_selling_points: 'AI camera, 7 years of updates',
    };

    render(<TrendsPage />);
    await user.click(screen.getByText('Review'));

    expect(screen.getByText('Campaign Summary')).toBeInTheDocument();
    expect(screen.getByText('Google Pixel')).toBeInTheDocument();
    expect(screen.getByText('Pixel 9 Pro')).toBeInTheDocument();
    expect(screen.getByText('Tech-savvy millennials')).toBeInTheDocument();
    expect(screen.getByText('AI camera, 7 years of updates')).toBeInTheDocument();
  });

  it('shows selected trends on Review tab', async () => {
    const user = userEvent.setup();
    mockStoreState.selectedSearchTrends = [
      { rank: 1, title: 'AI Photography Trends', relatedQueries: '', formattedTraffic: '100K+', trendDate: '' },
    ];
    mockStoreState.selectedYtTrends = [
      { rank: 1, title: 'Best Pixel Camera Review', description: '', channelName: 'TechReview', viewCount: '1M', publishedAt: '' },
    ];

    render(<TrendsPage />);
    await user.click(screen.getByText('Review'));

    expect(screen.getByText('Selected Trends')).toBeInTheDocument();
    expect(screen.getByText(/AI Photography Trends/)).toBeInTheDocument();
    expect(screen.getByText(/Best Pixel Camera Review/)).toBeInTheDocument();
  });

  it('disables launch button when config is incomplete', async () => {
    const user = userEvent.setup();
    render(<TrendsPage />);

    await user.click(screen.getByText('Review'));

    const launchButton = screen.getByText('Add Execution Run to Orchestrator');
    expect(launchButton.closest('button')).toBeDisabled();
  });

  it('shows missing items warnings on Review tab', async () => {
    const user = userEvent.setup();
    render(<TrendsPage />);

    await user.click(screen.getByText('Review'));

    expect(screen.getByText(/Missing: Brand or Product/)).toBeInTheDocument();
    expect(screen.getByText(/Missing: At least 1 trend/)).toBeInTheDocument();
  });

  it('navigates to /orchestration on launch when ready', async () => {
    mockStoreState.isReadyToLaunch.mockReturnValue({ ready: true, missing: [] });
    mockStoreState.config = { brand: 'Google', target_product: 'Pixel', target_audience: '', key_selling_points: '' };
    mockStoreState.selectedSearchTrends = [{ rank: 1, title: 'Test Trend' }];

    const user = userEvent.setup();
    render(<TrendsPage />);

    await user.click(screen.getByText('Review'));

    const launchButton = screen.getByText('Add Execution Run to Orchestrator');
    expect(launchButton.closest('button')).not.toBeDisabled();

    await user.click(launchButton);
    expect(mockNavigate).toHaveBeenCalledWith('/orchestration');
  });
});
