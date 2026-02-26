import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '../test-utils';
import userEvent from '@testing-library/user-event';

// Mock useNarrative hook
const mockSendMessage = vi.fn();
const mockNarrativeState = {
  messages: [] as any[],
  scenes: [] as any[],
  narrativeArc: undefined as any,
  isStreaming: false,
  sendMessage: mockSendMessage,
  reorderScenes: vi.fn(),
  updateScene: vi.fn(),
  updateNarrativeArc: vi.fn(),
};

vi.mock('../../features/narrative/useNarrative', () => ({
  useNarrative: () => mockNarrativeState,
}));

const { NarrativePage } = await import('../../features/narrative/NarrativePage');

describe('CUJ 3b: Narrative Studio', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockNarrativeState.messages = [];
    mockNarrativeState.scenes = [];
    mockNarrativeState.narrativeArc = undefined;
    mockNarrativeState.isStreaming = false;
  });

  it('renders narrative interface with heading', () => {
    render(<NarrativePage />);

    expect(screen.getByText('Narrative Interface')).toBeInTheDocument();
    expect(screen.getByText(/Collaborate with AI to craft and refine/)).toBeInTheDocument();
  });

  it('renders storyboard and narrative arc tabs', () => {
    render(<NarrativePage />);

    expect(screen.getByText(/Storyboard/)).toBeInTheDocument();
    expect(screen.getByText('Narrative Arc')).toBeInTheDocument();
  });

  it('renders chat input for text feedback', () => {
    render(<NarrativePage />);

    expect(screen.getByPlaceholderText('Describe your vision for the commercial...')).toBeInTheDocument();
    expect(screen.getByText('Send')).toBeInTheDocument();
  });

  it('allows submitting text feedback via chat', async () => {
    const user = userEvent.setup();
    render(<NarrativePage />);

    const input = screen.getByPlaceholderText('Describe your vision for the commercial...');
    await user.type(input, 'Make it more dramatic');
    await user.click(screen.getByText('Send'));

    expect(mockSendMessage).toHaveBeenCalledWith('Make it more dramatic');
  });

  it('shows quick action buttons', () => {
    render(<NarrativePage />);

    expect(screen.getByText('More dramatic')).toBeInTheDocument();
    expect(screen.getByText('Lighter tone')).toBeInTheDocument();
    expect(screen.getByText('Add humor')).toBeInTheDocument();
    expect(screen.getByText('Focus on product')).toBeInTheDocument();
  });

  it('shows "No messages yet" when chat is empty', () => {
    render(<NarrativePage />);

    expect(screen.getByText('No messages yet')).toBeInTheDocument();
  });

  it.skip('renders PDF preview of narrative document — NOT IMPLEMENTED', () => {
    // TODO: CUJ 3.2 specifies PDF rendering of the narrative document.
    // The NarrativePage currently has chat + storyboard but no PDF viewer component.
    // Implement a PDF viewer/renderer to display the narrative as a formatted document.
  });
});
