import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '../test-utils';
import { AppShell } from '../../components/layout/AppShell';

// Mock VoiceAssistantFAB to avoid complex voice dependencies
vi.mock('../../features/voice/VoiceAssistantFAB', () => ({
  VoiceAssistantFAB: () => (
    <button aria-label="Voice Assistant" data-testid="voice-fab">
      Voice FAB
    </button>
  ),
}));

describe('AppShell', () => {
  it('renders header component', () => {
    render(<AppShell />);

    const header = document.querySelector('header');
    expect(header).toBeInTheDocument();
  });

  it('renders sidebar component', () => {
    render(<AppShell />);

    const aside = document.querySelector('aside');
    expect(aside).toBeInTheDocument();
  });

  it('renders main content area', () => {
    render(<AppShell />);

    const main = screen.getByRole('main');
    expect(main).toBeInTheDocument();
  });

  it('applies correct layout structure', () => {
    const { container } = render(<AppShell />);

    const rootDiv = container.firstChild as HTMLElement;
    expect(rootDiv).toHaveClass('flex', 'h-screen', 'flex-col');
  });

  it('main content area is scrollable', () => {
    render(<AppShell />);

    const main = screen.getByRole('main');
    expect(main).toHaveClass('overflow-y-auto');
  });

  it('renders VoiceAssistantFAB', () => {
    render(<AppShell />);

    expect(screen.getByTestId('voice-fab')).toBeInTheDocument();
  });

  it('does not have "Voice Assistant" sidebar link', () => {
    render(<AppShell />);

    expect(screen.queryByText('Voice Assistant')).not.toBeInTheDocument();
  });

  it('sidebar shows "Configure" instead of "Trends"', () => {
    render(<AppShell />);

    expect(screen.getByText('Configure')).toBeInTheDocument();
    expect(screen.queryByText('Trends')).not.toBeInTheDocument();
  });

  it('sidebar shows "Evaluation Studio" instead of "Rating"', () => {
    render(<AppShell />);

    expect(screen.getByText('Evaluation Studio')).toBeInTheDocument();
    expect(screen.queryByText('Rating')).not.toBeInTheDocument();
  });
});
