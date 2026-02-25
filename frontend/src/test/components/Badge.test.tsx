import { describe, it, expect } from 'vitest';
import { render, screen } from '../test-utils';
import { Badge } from '../../components/ui/Badge';

describe('Badge', () => {
  it('renders with children text', () => {
    render(<Badge>New</Badge>);

    expect(screen.getByText('New')).toBeInTheDocument();
  });

  describe('variants', () => {
    it('renders default variant with correct colors', () => {
      render(<Badge variant="default">Default</Badge>);

      expect(screen.getByText('Default')).toHaveClass('bg-zinc-700', 'text-zinc-100');
    });

    it('renders success variant with correct colors', () => {
      render(<Badge variant="success">Success</Badge>);

      expect(screen.getByText('Success')).toHaveClass('bg-green-600', 'text-white');
    });

    it('renders warning variant with correct colors', () => {
      render(<Badge variant="warning">Warning</Badge>);

      expect(screen.getByText('Warning')).toHaveClass('bg-yellow-600', 'text-white');
    });

    it('renders error variant with correct colors', () => {
      render(<Badge variant="error">Error</Badge>);

      expect(screen.getByText('Error')).toHaveClass('bg-red-600', 'text-white');
    });

    it('renders info variant with correct colors', () => {
      render(<Badge variant="info">Info</Badge>);

      expect(screen.getByText('Info')).toHaveClass('bg-blue-600', 'text-white');
    });
  });

  it('applies default variant when none specified', () => {
    render(<Badge>Badge</Badge>);

    expect(screen.getByText('Badge')).toHaveClass('bg-zinc-700');
  });

  it('applies custom className', () => {
    render(<Badge className="custom-class">Badge</Badge>);

    expect(screen.getByText('Badge')).toHaveClass('custom-class');
  });

  it('applies base styling', () => {
    render(<Badge>Badge</Badge>);

    expect(screen.getByText('Badge')).toHaveClass('rounded-full', 'px-2.5', 'py-0.5', 'text-xs');
  });

  it('forwards ref', () => {
    const ref = vi.fn();

    render(<Badge ref={ref}>Badge</Badge>);

    expect(ref).toHaveBeenCalled();
  });
});
