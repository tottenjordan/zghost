import { describe, it, expect } from 'vitest';
import { render, screen } from '../test-utils';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';

describe('Card', () => {
  it('renders children', () => {
    render(<Card>Card content</Card>);

    expect(screen.getByText('Card content')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    render(<Card className="custom-class">Content</Card>);

    expect(screen.getByText('Content')).toHaveClass('custom-class');
  });

  it('applies default styling', () => {
    render(<Card>Content</Card>);

    expect(screen.getByText('Content')).toHaveClass('rounded-xl', 'border');
  });
});

describe('CardHeader', () => {
  it('renders children', () => {
    render(<CardHeader>Header content</CardHeader>);

    expect(screen.getByText('Header content')).toBeInTheDocument();
  });

  it('applies header styling', () => {
    render(<CardHeader>Header</CardHeader>);

    expect(screen.getByText('Header')).toHaveClass('flex', 'flex-col', 'p-6');
  });
});

describe('CardTitle', () => {
  it('renders as h3 element', () => {
    render(<CardTitle>Title</CardTitle>);

    expect(screen.getByRole('heading', { level: 3 })).toHaveTextContent('Title');
  });

  it('applies title styling', () => {
    render(<CardTitle>Title</CardTitle>);

    expect(screen.getByRole('heading')).toHaveClass('text-lg', 'font-semibold');
  });
});

describe('CardContent', () => {
  it('renders children', () => {
    render(<CardContent>Content text</CardContent>);

    expect(screen.getByText('Content text')).toBeInTheDocument();
  });

  it('applies content styling', () => {
    render(<CardContent>Content</CardContent>);

    expect(screen.getByText('Content')).toHaveClass('p-6', 'pt-0');
  });
});

describe('Card composition', () => {
  it('renders complete card structure', () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>Card Title</CardTitle>
        </CardHeader>
        <CardContent>Card body text</CardContent>
      </Card>
    );

    expect(screen.getByRole('heading', { level: 3 })).toHaveTextContent('Card Title');
    expect(screen.getByText('Card body text')).toBeInTheDocument();
  });
});
