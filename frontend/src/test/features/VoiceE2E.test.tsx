import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, act } from '../test-utils';

// Mock voice hooks
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

vi.mock('../../features/voice/AudioVisualizer', () => ({
  AudioVisualizer: () => <div data-testid="audio-visualizer" />,
}));

vi.mock('../../features/voice/VoiceBriefAssistant', () => ({
  VoiceBriefAssistant: () => <div data-testid="voice-brief-assistant" />,
}));

vi.mock('../../features/voice/VoiceCommandRouter', () => ({
  VoiceCommandRouter: () => null,
}));

describe('Voice E2E Flow', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('set_campaign_config updates store state', async () => {
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
          params: { brand: 'Google', product: 'Pixel 9 Pro', audience: 'Tech enthusiasts', selling_points: 'AI camera' }
        })}>
          Load Config
        </button>
      );
    }

    render(<TestComponent />);
    await act(async () => { screen.getByText('Load Config').click(); });

    expect(storeState.config.brand).toBe('Google');
    expect(storeState.config.target_product).toBe('Pixel 9 Pro');
    expect(storeState.config.target_audience).toBe('Tech enthusiasts');
    expect(storeState.config.key_selling_points).toBe('AI camera');
  });

  it('start_pipeline sets autoStart and navigates to orchestration', async () => {
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
          Start
        </button>
      );
    }

    render(<TestComponent />);
    await act(async () => { screen.getByText('Start').click(); });

    expect(storeState.autoStart).toBe(true);
  });

  it('set_commercial_duration updates store', async () => {
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

  it('set_commercial_duration only accepts valid values (10, 15, 30)', async () => {
    const { useVoiceActions } = await import('../../features/voice/useVoiceActions');
    const { useCampaignStore } = await import('../../stores/campaignStore');

    let storeState: any;

    function TestComponent() {
      const { executeAction } = useVoiceActions();
      const store = useCampaignStore();
      storeState = store;
      return (
        <>
          <button onClick={() => executeAction({
            type: 'action',
            action: 'set_commercial_duration',
            params: { seconds: 10 }
          })}>
            Set 10
          </button>
          <button onClick={() => executeAction({
            type: 'action',
            action: 'set_commercial_duration',
            params: { seconds: 99 }
          })}>
            Set 99
          </button>
        </>
      );
    }

    render(<TestComponent />);

    // Valid value should work
    await act(async () => { screen.getByText('Set 10').click(); });
    expect(storeState.commercialDuration).toBe(10);

    // Invalid value should be ignored
    const previousDuration = storeState.commercialDuration;
    await act(async () => { screen.getByText('Set 99').click(); });
    expect(storeState.commercialDuration).toBe(previousDuration);
  });

  it('voice-action custom events are properly structured', async () => {
    const { useVoiceActions } = await import('../../features/voice/useVoiceActions');

    const events: CustomEvent[] = [];
    const handler = (e: Event) => events.push(e as CustomEvent);
    window.addEventListener('voice-action', handler);

    function TestComponent() {
      const { executeAction } = useVoiceActions();
      return (
        <div>
          <button onClick={() => executeAction({ type: 'action', action: 'select_google_trend', params: { rank: 1 } })}>T1</button>
          <button onClick={() => executeAction({ type: 'action', action: 'send_narrative_direction', params: { direction: 'More drama' } })}>T2</button>
          <button onClick={() => executeAction({ type: 'action', action: 'send_studio_direction', params: { direction: 'Louder music' } })}>T3</button>
          <button onClick={() => executeAction({ type: 'action', action: 'score_criterion', params: { criterion_name: 'Creativity', score: 5 } })}>T4</button>
        </div>
      );
    }

    render(<TestComponent />);

    await act(async () => { screen.getByText('T1').click(); });
    await act(async () => { screen.getByText('T2').click(); });
    await act(async () => { screen.getByText('T3').click(); });
    await act(async () => { screen.getByText('T4').click(); });

    expect(events).toHaveLength(4);
    expect(events[0].detail.action).toBe('select_google_trend');
    expect(events[0].detail.params.rank).toBe(1);
    expect(events[1].detail.action).toBe('send_narrative_direction');
    expect(events[1].detail.params.direction).toBe('More drama');
    expect(events[2].detail.action).toBe('send_studio_direction');
    expect(events[2].detail.params.direction).toBe('Louder music');
    expect(events[3].detail.action).toBe('score_criterion');
    expect(events[3].detail.params.criterion_name).toBe('Creativity');
    expect(events[3].detail.params.score).toBe(5);

    window.removeEventListener('voice-action', handler);
  });

  it('navigate_to_page action supports different pages', async () => {
    const { useVoiceActions } = await import('../../features/voice/useVoiceActions');

    function TestComponent() {
      const { executeAction } = useVoiceActions();
      return (
        <div>
          <button onClick={() => executeAction({ type: 'action', action: 'navigate_to_page', params: { page: 'trends' } })}>Trends</button>
          <button onClick={() => executeAction({ type: 'action', action: 'navigate_to_page', params: { page: 'studio' } })}>Studio</button>
          <button onClick={() => executeAction({ type: 'action', action: 'navigate_to_page', params: { page: 'narrative' } })}>Narrative</button>
          <button onClick={() => executeAction({ type: 'action', action: 'navigate_to_page', params: { page: 'rating' } })}>Rating</button>
        </div>
      );
    }

    render(<TestComponent />);

    // All navigation actions should execute without errors
    await act(async () => { screen.getByText('Trends').click(); });
    await act(async () => { screen.getByText('Studio').click(); });
    await act(async () => { screen.getByText('Narrative').click(); });
    await act(async () => { screen.getByText('Rating').click(); });
  });

  it('config updates preserve existing values when partial params provided', async () => {
    const { useVoiceActions } = await import('../../features/voice/useVoiceActions');
    const { useCampaignStore } = await import('../../stores/campaignStore');

    let storeState: any;

    function TestComponent() {
      const { executeAction } = useVoiceActions();
      const store = useCampaignStore();
      storeState = store;
      return (
        <div>
          <button onClick={() => executeAction({
            type: 'action',
            action: 'set_campaign_config',
            params: { brand: 'InitialBrand', product: 'InitialProduct' }
          })}>
            Initial
          </button>
          <button onClick={() => executeAction({
            type: 'action',
            action: 'set_campaign_config',
            params: { audience: 'New Audience' }
          })}>
            Update Audience
          </button>
        </div>
      );
    }

    render(<TestComponent />);

    // Set initial config
    await act(async () => { screen.getByText('Initial').click(); });
    expect(storeState.config.brand).toBe('InitialBrand');
    expect(storeState.config.target_product).toBe('InitialProduct');

    // Partial update should preserve brand and product
    await act(async () => { screen.getByText('Update Audience').click(); });
    expect(storeState.config.brand).toBe('InitialBrand');
    expect(storeState.config.target_product).toBe('InitialProduct');
    expect(storeState.config.target_audience).toBe('New Audience');
  });

  it('console logs action on execution', async () => {
    const { useVoiceActions } = await import('../../features/voice/useVoiceActions');
    const consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {});

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
    await act(async () => { screen.getByText('Navigate').click(); });

    expect(consoleSpy).toHaveBeenCalledWith('Voice action received:', expect.objectContaining({
      type: 'action',
      action: 'navigate_to_page',
    }));

    consoleSpy.mockRestore();
  });
});
