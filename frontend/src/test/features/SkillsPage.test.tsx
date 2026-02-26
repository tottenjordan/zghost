import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '../test-utils';
import userEvent from '@testing-library/user-event';
import { SkillsPage } from '../../features/skills/SkillsPage';

describe('SkillsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the page title', () => {
    render(<SkillsPage />);
    expect(screen.getByText('Skills Architecture')).toBeInTheDocument();
  });

  it('renders all 5 skill cards', () => {
    render(<SkillsPage />);
    expect(screen.getByTestId('skill-card-trend-discovery')).toBeInTheDocument();
    expect(screen.getByTestId('skill-card-market-research')).toBeInTheDocument();
    expect(screen.getByTestId('skill-card-ad-creative')).toBeInTheDocument();
    expect(screen.getByTestId('skill-card-av-studio')).toBeInTheDocument();
    expect(screen.getByTestId('skill-card-focus-group')).toBeInTheDocument();
  });

  it('renders skill names', () => {
    render(<SkillsPage />);
    expect(screen.getByText('Trend Discovery')).toBeInTheDocument();
    expect(screen.getByText('Market Research')).toBeInTheDocument();
    expect(screen.getByText('Ad Creative')).toBeInTheDocument();
    expect(screen.getByText('AV Studio')).toBeInTheDocument();
    expect(screen.getByText('Focus Group')).toBeInTheDocument();
  });

  it('renders team owners', () => {
    render(<SkillsPage />);
    expect(screen.getByText('Data/Analytics Team')).toBeInTheDocument();
    expect(screen.getByText('Research/Content Team')).toBeInTheDocument();
    expect(screen.getByText('Creative Team')).toBeInTheDocument();
    expect(screen.getByText('AV Production Team')).toBeInTheDocument();
    expect(screen.getByText('QA/Evaluation Team')).toBeInTheDocument();
  });

  it('renders tabs for Skills, Architecture, and Memory Bank', () => {
    render(<SkillsPage />);
    // Check for tab content by finding buttons with role
    const tabs = screen.getAllByRole('button');
    const tabText = tabs.map(tab => tab.textContent).join(' ');
    expect(tabText).toContain('Skills');
    expect(tabText).toContain('Architecture');
    expect(tabText).toContain('Memory Bank');
  });

  it('clicking a skill card toggles highlight', async () => {
    const user = userEvent.setup();
    render(<SkillsPage />);

    const card = screen.getByTestId('skill-card-trend-discovery');

    // Click to highlight
    await user.click(card);
    expect(card.className).toContain('ring-2');

    // Click again to unhighlight
    await user.click(card);
    expect(card.className).not.toContain('ring-2');
  });

  it('renders architecture tab content when clicked', async () => {
    const user = userEvent.setup();
    render(<SkillsPage />);

    await user.click(screen.getByText('Architecture'));
    // Architecture diagram should be visible (SVG element)
    expect(document.querySelector('svg')).toBeInTheDocument();
  });

  it('renders memory explorer tab content when clicked', async () => {
    const user = userEvent.setup();
    render(<SkillsPage />);

    await user.click(screen.getByText('Memory Bank'));
    // Memory explorer should show search input
    expect(screen.getByPlaceholderText(/search memories/i)).toBeInTheDocument();
  });

  it('renders skill descriptions', () => {
    render(<SkillsPage />);
    expect(screen.getByText(/Campaign metadata configuration/)).toBeInTheDocument();
    expect(screen.getByText(/Parallel web research pipeline/)).toBeInTheDocument();
    expect(screen.getByText(/Ad copy drafting/)).toBeInTheDocument();
  });

  it('renders skill tools', () => {
    render(<SkillsPage />);
    expect(screen.getByText('get_google_trends')).toBeInTheDocument();
    expect(screen.getByText('web_search')).toBeInTheDocument();
    expect(screen.getByText('generate_image')).toBeInTheDocument();
  });

  it('renders skill version badges', () => {
    render(<SkillsPage />);
    const versionBadges = screen.getAllByText(/v1\.0\.0/);
    expect(versionBadges).toHaveLength(5);
  });

  it('renders state reads and writes sections', () => {
    render(<SkillsPage />);
    const readsSections = screen.getAllByText('Reads');
    const writesSections = screen.getAllByText('Writes');
    expect(readsSections.length).toBeGreaterThan(0);
    expect(writesSections.length).toBeGreaterThan(0);
  });
});
