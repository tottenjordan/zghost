import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '../test-utils';
import userEvent from '@testing-library/user-event';

// Mock the voice session hook
vi.mock('../../features/voice/useVoiceSession', () => ({
  useVoiceSession: () => ({
    connectionState: 'idle',
    transcript: [],
    error: null,
    toggleRecording: vi.fn(),
    disconnect: vi.fn(),
    isRecording: false,
    isConnected: false,
    addUserMessage: vi.fn(),
    connect: vi.fn(),
  }),
}));

// Mock VoiceBriefAssistant to avoid complex dependencies
vi.mock('../../features/voice/VoiceBriefAssistant', () => ({
  VoiceBriefAssistant: ({ onClose }: { onClose?: () => void; isFloating?: boolean }) => (
    <div data-testid="voice-brief-assistant">
      Voice Brief Assistant Panel
      {onClose && <button onClick={onClose}>Close</button>}
    </div>
  ),
}));

// Mock AudioVisualizer
vi.mock('../../features/voice/AudioVisualizer', () => ({
  AudioVisualizer: ({ isActive }: { isActive: boolean; isSpeaking?: boolean; className?: string }) => (
    <div data-testid="audio-visualizer" data-active={isActive}>
      Audio Visualizer
    </div>
  ),
}));

const { VoiceAssistantFAB } = await import('../../features/voice/VoiceAssistantFAB');

describe('VoiceAssistantFAB', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders a mic button', () => {
    render(<VoiceAssistantFAB />);

    const button = screen.getByLabelText('Voice Assistant');
    expect(button).toBeInTheDocument();
  });

  it('button is fixed position at bottom-right', () => {
    render(<VoiceAssistantFAB />);

    const button = screen.getByLabelText('Voice Assistant');
    expect(button).toHaveClass('fixed', 'bottom-6', 'right-6');
  });

  it('click expands the voice panel', async () => {
    const user = userEvent.setup();
    render(<VoiceAssistantFAB />);

    expect(screen.queryByTestId('voice-brief-assistant')).not.toBeInTheDocument();

    await user.click(screen.getByLabelText('Voice Assistant'));

    expect(screen.getByTestId('voice-brief-assistant')).toBeInTheDocument();
  });

  it('click again collapses back to circle', async () => {
    const user = userEvent.setup();
    render(<VoiceAssistantFAB />);

    // Expand
    await user.click(screen.getByLabelText('Voice Assistant'));
    expect(screen.getByTestId('voice-brief-assistant')).toBeInTheDocument();

    // Collapse
    await user.click(screen.getByLabelText('Voice Assistant'));
    expect(screen.queryByTestId('voice-brief-assistant')).not.toBeInTheDocument();
  });
});
