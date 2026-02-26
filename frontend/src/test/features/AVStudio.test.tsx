import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '../test-utils';

// Mock useStudio hook
const mockStudioState = {
  clips: [] as any[],
  characters: [] as any[],
  commercial: undefined as any,
  voiceSamples: [] as any[],
  musicSamples: [] as any[],
  selectedVoice: null as any,
  selectedMusic: null as any,
  isLoading: false,
  reorderClips: vi.fn(),
  removeClip: vi.fn(),
  selectVoice: vi.fn(),
  generateVoiceSample: vi.fn(),
  selectMusic: vi.fn(),
  generateMusicSample: vi.fn(),
  removeMusicSample: vi.fn(),
};

vi.mock('../../features/studio/useStudio', () => ({
  useStudio: () => mockStudioState,
}));

const { StudioPage } = await import('../../features/studio/StudioPage');

describe('CUJ 3c: AV Studio', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockStudioState.clips = [];
    mockStudioState.characters = [];
    mockStudioState.commercial = undefined;
    mockStudioState.isLoading = false;
  });

  it('renders AV Studio with heading', () => {
    render(<StudioPage />);

    expect(screen.getByText('AV Studio')).toBeInTheDocument();
    expect(screen.getByText(/Video editing workspace/)).toBeInTheDocument();
  });

  it('shows clip library tab', () => {
    render(<StudioPage />);

    expect(screen.getByText(/Clips/)).toBeInTheDocument();
  });

  it('shows voice and music tabs', () => {
    render(<StudioPage />);

    expect(screen.getByText('Voice')).toBeInTheDocument();
    expect(screen.getByText('Music')).toBeInTheDocument();
  });

  it('shows timeline tab', () => {
    render(<StudioPage />);

    // Multiple elements contain "Timeline" (tab + editor), so use getAllByText
    const timelineElements = screen.getAllByText(/Timeline/);
    expect(timelineElements.length).toBeGreaterThan(0);
  });

  it('shows characters tab', () => {
    render(<StudioPage />);

    expect(screen.getByText(/Characters/)).toBeInTheDocument();
  });

  it('shows agent activity tab', () => {
    render(<StudioPage />);

    expect(screen.getByText('Agent Activity')).toBeInTheDocument();
  });

  it('shows session ID when provided via URL param', () => {
    // Set URL search param before render
    const originalLocation = window.location;
    Object.defineProperty(window, 'location', {
      value: { ...originalLocation, search: '?session=test-session-abc' },
      writable: true,
    });

    render(<StudioPage />);

    expect(screen.getByText('Session: test-session-abc')).toBeInTheDocument();

    // Restore
    Object.defineProperty(window, 'location', {
      value: originalLocation,
      writable: true,
    });
  });

  it('shows loading state when studio data is loading', () => {
    mockStudioState.isLoading = true;
    render(<StudioPage />);

    expect(screen.getByText('Loading studio data...')).toBeInTheDocument();
  });
});
