import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '../test-utils';
import userEvent from '@testing-library/user-event';
import { SearchTrendCard, YTTrendCard } from '../../features/trends/TrendCard';
import { mockSearchTrends, mockYTTrends } from '../mocks/fixtures';

describe('SearchTrendCard', () => {
  const mockTrend = mockSearchTrends[0];

  it('renders search trend data', () => {
    render(<SearchTrendCard trend={mockTrend} selected={false} onToggle={vi.fn()} />);

    expect(screen.getByText(mockTrend.title)).toBeInTheDocument();
    expect(screen.getByText(mockTrend.formattedTraffic)).toBeInTheDocument();
  });

  it('displays related queries', () => {
    render(<SearchTrendCard trend={mockTrend} selected={false} onToggle={vi.fn()} />);

    expect(screen.getByText(/Related:/)).toBeInTheDocument();
    expect(screen.getByText(mockTrend.relatedQueries)).toBeInTheDocument();
  });

  it('shows traffic badge', () => {
    render(<SearchTrendCard trend={mockTrend} selected={false} onToggle={vi.fn()} />);

    const badge = screen.getByText(mockTrend.formattedTraffic);
    expect(badge).toHaveClass('text-blue-400'); // info variant
  });

  it('selection toggle works', async () => {
    const handleToggle = vi.fn();
    const user = userEvent.setup();

    render(<SearchTrendCard trend={mockTrend} selected={false} onToggle={handleToggle} />);

    const checkbox = screen.getByRole('checkbox');
    await user.click(checkbox);

    expect(handleToggle).toHaveBeenCalledTimes(1);
  });

  it('applies selected styling when selected', () => {
    const { container } = render(
      <SearchTrendCard trend={mockTrend} selected={true} onToggle={vi.fn()} />
    );

    const card = container.firstChild as HTMLElement;
    expect(card).toHaveClass('ring-2', 'ring-blue-500');
  });

  it('expands to show articles', async () => {
    const user = userEvent.setup();

    render(<SearchTrendCard trend={mockTrend} selected={false} onToggle={vi.fn()} />);

    const expandButton = screen.getByText(/Show.*article/);
    await user.click(expandButton);

    expect(screen.getByText(mockTrend.articles![0].title)).toBeInTheDocument();
    expect(screen.getByText(/Hide.*article/)).toBeInTheDocument();
  });

  it('collapses articles when hide is clicked', async () => {
    const user = userEvent.setup();

    render(<SearchTrendCard trend={mockTrend} selected={false} onToggle={vi.fn()} />);

    // Expand
    await user.click(screen.getByText(/Show.*article/));
    expect(screen.getByText(mockTrend.articles![0].title)).toBeInTheDocument();

    // Collapse
    await user.click(screen.getByText(/Hide.*article/));
    expect(screen.queryByText(mockTrend.articles![0].snippet)).not.toBeInTheDocument();
  });

  it('clicking card toggles selection', async () => {
    const handleToggle = vi.fn();
    const user = userEvent.setup();
    const { container } = render(
      <SearchTrendCard trend={mockTrend} selected={false} onToggle={handleToggle} />
    );

    await user.click(container.firstChild as HTMLElement);

    expect(handleToggle).toHaveBeenCalled();
  });
});

describe('YTTrendCard', () => {
  const mockTrend = mockYTTrends[0];

  it('renders YouTube trend data', () => {
    render(<YTTrendCard trend={mockTrend} selected={false} onToggle={vi.fn()} />);

    expect(screen.getByText(mockTrend.title)).toBeInTheDocument();
    expect(screen.getByText(mockTrend.channelName)).toBeInTheDocument();
    expect(screen.getByText(`${mockTrend.viewCount} views`)).toBeInTheDocument();
  });

  it('displays rank badge', () => {
    render(<YTTrendCard trend={mockTrend} selected={false} onToggle={vi.fn()} />);

    const badge = screen.getByText(`#${mockTrend.rank}`);
    expect(badge).toHaveClass('text-emerald-400'); // success variant
  });

  it('selection toggle works', async () => {
    const handleToggle = vi.fn();
    const user = userEvent.setup();

    render(<YTTrendCard trend={mockTrend} selected={false} onToggle={handleToggle} />);

    const checkbox = screen.getByRole('checkbox');
    await user.click(checkbox);

    expect(handleToggle).toHaveBeenCalledTimes(1);
  });

  it('applies selected styling when selected', () => {
    const { container } = render(
      <YTTrendCard trend={mockTrend} selected={true} onToggle={vi.fn()} />
    );

    const card = container.firstChild as HTMLElement;
    expect(card).toHaveClass('ring-2', 'ring-blue-500');
  });

  it('expands to show description', async () => {
    const user = userEvent.setup();

    render(<YTTrendCard trend={mockTrend} selected={false} onToggle={vi.fn()} />);

    const expandButton = screen.getByText('Show description');
    await user.click(expandButton);

    expect(screen.getByText(mockTrend.description)).toBeInTheDocument();
    expect(screen.getByText('Hide description')).toBeInTheDocument();
  });

  it('renders thumbnail when available', () => {
    render(<YTTrendCard trend={mockTrend} selected={false} onToggle={vi.fn()} />);

    const image = screen.getByRole('img', { name: mockTrend.title });
    expect(image).toHaveAttribute('src', mockTrend.thumbnail);
  });

  it('renders YouTube link', () => {
    render(<YTTrendCard trend={mockTrend} selected={false} onToggle={vi.fn()} />);

    const link = screen.getByText('Watch on YouTube →');
    expect(link).toHaveAttribute('href', mockTrend.videoUrl);
    expect(link).toHaveAttribute('target', '_blank');
  });

  it('displays published time', () => {
    render(<YTTrendCard trend={mockTrend} selected={false} onToggle={vi.fn()} />);

    expect(screen.getByText(mockTrend.publishedTime)).toBeInTheDocument();
  });
});
