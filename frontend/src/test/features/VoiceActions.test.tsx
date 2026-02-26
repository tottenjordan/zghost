import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, act } from '../test-utils';

// Mock the voice hooks
vi.mock('../../features/voice/useVoiceSession', () => ({
  useVoiceSession: () => ({
    connectionState: 'idle',
    transcript: [],
    error: null,
    toggleRecording: vi.fn(),
    disconnect: vi.fn(),
    isRecording: false,
    isConnected: false,
    sendContext: vi.fn(),
  }),
}));

// Mock AudioVisualizer
vi.mock('../../features/voice/AudioVisualizer', () => ({
  AudioVisualizer: () => <div data-testid="audio-visualizer" />,
}));

// Mock VoiceBriefAssistant
vi.mock('../../features/voice/VoiceBriefAssistant', () => ({
  VoiceBriefAssistant: () => <div data-testid="voice-brief-assistant" />,
}));

// Mock VoiceCommandRouter
vi.mock('../../features/voice/VoiceCommandRouter', () => ({
  VoiceCommandRouter: () => null,
}));

describe('Voice Action Event Dispatching', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('dispatches set_campaign_config action and updates store', async () => {
    const { useVoiceActions } = await import('../../features/voice/useVoiceActions');
    const { useCampaignStore } = await import('../../stores/campaignStore');

    let storeState: any;

    function TestComponent() {
      const { executeAction } = useVoiceActions();
      const store = useCampaignStore();
      storeState = store;
      return (
        <button onClick={() => executeAction({
          type: 'action',
          action: 'set_campaign_config',
          params: { brand: 'TestBrand', product: 'TestProduct' }
        })}>
          Set Config
        </button>
      );
    }

    render(<TestComponent />);
    const button = screen.getByText('Set Config');
    await act(async () => { button.click(); });

    expect(storeState.config.brand).toBe('TestBrand');
    expect(storeState.config.target_product).toBe('TestProduct');
  });

  it('dispatches navigate_to_page action', async () => {
    const { useVoiceActions } = await import('../../features/voice/useVoiceActions');

    function TestComponent() {
      const { executeAction } = useVoiceActions();
      return (
        <button onClick={() => executeAction({
          type: 'action',
          action: 'navigate_to_page',
          params: { page: 'studio' }
        })}>
          Navigate
        </button>
      );
    }

    render(<TestComponent />);
    const button = screen.getByText('Navigate');
    await act(async () => { button.click(); });
  });

  it('dispatches select_google_trend as custom event', async () => {
    const { useVoiceActions } = await import('../../features/voice/useVoiceActions');
    const eventSpy = vi.fn();
    window.addEventListener('voice-action', eventSpy);

    function TestComponent() {
      const { executeAction } = useVoiceActions();
      return (
        <button onClick={() => executeAction({
          type: 'action',
          action: 'select_google_trend',
          params: { rank: 1 }
        })}>
          Select Trend
        </button>
      );
    }

    render(<TestComponent />);
    await act(async () => { screen.getByText('Select Trend').click(); });

    expect(eventSpy).toHaveBeenCalledTimes(1);
    const event = eventSpy.mock.calls[0][0] as CustomEvent;
    expect(event.detail.action).toBe('select_google_trend');
    expect(event.detail.params.rank).toBe(1);

    window.removeEventListener('voice-action', eventSpy);
  });

  it('dispatches select_youtube_trend as custom event', async () => {
    const { useVoiceActions } = await import('../../features/voice/useVoiceActions');
    const eventSpy = vi.fn();
    window.addEventListener('voice-action', eventSpy);

    function TestComponent() {
      const { executeAction } = useVoiceActions();
      return (
        <button onClick={() => executeAction({
          type: 'action',
          action: 'select_youtube_trend',
          params: { rank: 2 }
        })}>
          Select YT
        </button>
      );
    }

    render(<TestComponent />);
    await act(async () => { screen.getByText('Select YT').click(); });

    expect(eventSpy).toHaveBeenCalledTimes(1);
    const event = eventSpy.mock.calls[0][0] as CustomEvent;
    expect(event.detail.action).toBe('select_youtube_trend');
    expect(event.detail.params.rank).toBe(2);

    window.removeEventListener('voice-action', eventSpy);
  });

  it('dispatches send_narrative_direction as custom event', async () => {
    const { useVoiceActions } = await import('../../features/voice/useVoiceActions');
    const eventSpy = vi.fn();
    window.addEventListener('voice-action', eventSpy);

    function TestComponent() {
      const { executeAction } = useVoiceActions();
      return (
        <button onClick={() => executeAction({
          type: 'action',
          action: 'send_narrative_direction',
          params: { direction: 'Make it more dramatic' }
        })}>
          Send Direction
        </button>
      );
    }

    render(<TestComponent />);
    await act(async () => { screen.getByText('Send Direction').click(); });

    expect(eventSpy).toHaveBeenCalledTimes(1);
    const event = eventSpy.mock.calls[0][0] as CustomEvent;
    expect(event.detail.action).toBe('send_narrative_direction');
    expect(event.detail.params.direction).toBe('Make it more dramatic');

    window.removeEventListener('voice-action', eventSpy);
  });

  it('dispatches send_studio_direction as custom event', async () => {
    const { useVoiceActions } = await import('../../features/voice/useVoiceActions');
    const eventSpy = vi.fn();
    window.addEventListener('voice-action', eventSpy);

    function TestComponent() {
      const { executeAction } = useVoiceActions();
      return (
        <button onClick={() => executeAction({
          type: 'action',
          action: 'send_studio_direction',
          params: { direction: 'Add more bass' }
        })}>
          Studio Direction
        </button>
      );
    }

    render(<TestComponent />);
    await act(async () => { screen.getByText('Studio Direction').click(); });

    expect(eventSpy).toHaveBeenCalledTimes(1);
    const event = eventSpy.mock.calls[0][0] as CustomEvent;
    expect(event.detail.action).toBe('send_studio_direction');
    expect(event.detail.params.direction).toBe('Add more bass');

    window.removeEventListener('voice-action', eventSpy);
  });

  it('dispatches score_criterion as custom event', async () => {
    const { useVoiceActions } = await import('../../features/voice/useVoiceActions');
    const eventSpy = vi.fn();
    window.addEventListener('voice-action', eventSpy);

    function TestComponent() {
      const { executeAction } = useVoiceActions();
      return (
        <button onClick={() => executeAction({
          type: 'action',
          action: 'score_criterion',
          params: { criterion_name: 'Creativity', score: 4 }
        })}>
          Score
        </button>
      );
    }

    render(<TestComponent />);
    await act(async () => { screen.getByText('Score').click(); });

    expect(eventSpy).toHaveBeenCalledTimes(1);
    const event = eventSpy.mock.calls[0][0] as CustomEvent;
    expect(event.detail.action).toBe('score_criterion');
    expect(event.detail.params.criterion_name).toBe('Creativity');
    expect(event.detail.params.score).toBe(4);

    window.removeEventListener('voice-action', eventSpy);
  });

  it('logs warning for unknown action', async () => {
    const { useVoiceActions } = await import('../../features/voice/useVoiceActions');
    const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

    function TestComponent() {
      const { executeAction } = useVoiceActions();
      return (
        <button onClick={() => executeAction({
          type: 'action',
          action: 'unknown_action',
          params: {}
        })}>
          Unknown
        </button>
      );
    }

    render(<TestComponent />);
    await act(async () => { screen.getByText('Unknown').click(); });

    expect(consoleSpy).toHaveBeenCalledWith('Unknown voice action:', 'unknown_action');
    consoleSpy.mockRestore();
  });

  it('dispatches start_pipeline action and sets autoStart', async () => {
    const { useVoiceActions } = await import('../../features/voice/useVoiceActions');
    const { useCampaignStore } = await import('../../stores/campaignStore');

    let storeState: any;

    function TestComponent() {
      const { executeAction } = useVoiceActions();
      const store = useCampaignStore();
      storeState = store;
      return (
        <button onClick={() => executeAction({
          type: 'action',
          action: 'start_pipeline',
          params: {}
        })}>
          Start Pipeline
        </button>
      );
    }

    render(<TestComponent />);
    await act(async () => { screen.getByText('Start Pipeline').click(); });

    expect(storeState.autoStart).toBe(true);
  });

  it('dispatches set_commercial_duration action', async () => {
    const { useVoiceActions } = await import('../../features/voice/useVoiceActions');
    const { useCampaignStore } = await import('../../stores/campaignStore');

    let storeState: any;

    function TestComponent() {
      const { executeAction } = useVoiceActions();
      const store = useCampaignStore();
      storeState = store;
      return (
        <button onClick={() => executeAction({
          type: 'action',
          action: 'set_commercial_duration',
          params: { seconds: 15 }
        })}>
          Set Duration
        </button>
      );
    }

    render(<TestComponent />);
    await act(async () => { screen.getByText('Set Duration').click(); });

    expect(storeState.commercialDuration).toBe(15);
  });
});
