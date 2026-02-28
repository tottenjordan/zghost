import { describe, it, expect } from 'vitest';
import { render, screen } from '../test-utils';
import { ResultsGallery } from '../../features/orchestration/ResultsGallery';

describe('ResultsGallery', () => {
  it('renders "No results yet" when sessionState is empty', () => {
    render(<ResultsGallery sessionState={{}} />);

    expect(screen.getByText('No results yet')).toBeInTheDocument();
    expect(screen.getByText('Run the pipeline to generate ad creatives')).toBeInTheDocument();
  });

  it('renders ad copies when final_select_ad_copies is present', () => {
    const sessionState = {
      final_select_ad_copies: [
        { headline: 'Test Headline', body: 'Test body text', cta: 'Buy Now', score: 85 },
      ],
    };

    render(<ResultsGallery sessionState={sessionState} />);

    expect(screen.getByText('Test Headline')).toBeInTheDocument();
    expect(screen.getByText('Ad Copies')).toBeInTheDocument();
  });

  it('renders "View in Narrative" button when report is available', () => {
    const sessionState = {
      combined_final_cited_report: 'Full research report content here...',
      gcs_folder: 'test-folder-123',
    };

    render(<ResultsGallery sessionState={sessionState} />);

    expect(screen.getByText('View in Narrative')).toBeInTheDocument();
  });

  it('renders "Open in AV Studio" button when video is available', () => {
    const sessionState = {
      vid_artifact_keys: ['video1.mp4'],
      gcs_folder: 'test-folder-123',
    };

    render(<ResultsGallery sessionState={sessionState} />);

    expect(screen.getByText('Open in AV Studio')).toBeInTheDocument();
  });

  it('shows pipeline progress badges', () => {
    const sessionState = {
      combined_final_cited_report: 'Report content',
      final_select_ad_copies: [{ headline: 'Ad 1' }],
      final_visual_concepts: 'Visual concepts',
      img_artifact_keys: ['img1.png'],
      gcs_folder: 'test-folder',
    };

    render(<ResultsGallery sessionState={sessionState} />);

    expect(screen.getByText('Research Done')).toBeInTheDocument();
    expect(screen.getByText('1 Ad Copies')).toBeInTheDocument();
    expect(screen.getByText('Visuals Done')).toBeInTheDocument();
  });

  it('renders visual concepts section when present', () => {
    const sessionState = {
      final_visual_concepts: 'A vibrant scene showing the product...',
    };

    render(<ResultsGallery sessionState={sessionState} />);

    expect(screen.getByText('Visual Concepts')).toBeInTheDocument();
  });

  it('renders multiple ad copies', () => {
    const sessionState = {
      final_select_ad_copies: [
        { headline: 'Ad Copy 1', body: 'Body 1' },
        { headline: 'Ad Copy 2', body: 'Body 2' },
        { headline: 'Ad Copy 3', body: 'Body 3' },
      ],
    };

    render(<ResultsGallery sessionState={sessionState} />);

    expect(screen.getByText('Ad Copy 1')).toBeInTheDocument();
    expect(screen.getByText('Ad Copy 2')).toBeInTheDocument();
    expect(screen.getByText('Ad Copy 3')).toBeInTheDocument();
  });
});
