import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '../test-utils';
import userEvent from '@testing-library/user-event';
import { Button } from '../../components/ui/Button';

describe('Button', () => {
  it('renders with children text', () => {
    render(<Button>Click me</Button>);

    expect(screen.getByRole('button')).toHaveTextContent('Click me');
  });

  it('handles click events', async () => {
    const handleClick = vi.fn();
    const user = userEvent.setup();

    render(<Button onClick={handleClick}>Click me</Button>);

    await user.click(screen.getByRole('button'));

    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('renders disabled state', () => {
    const handleClick = vi.fn();

    render(<Button disabled onClick={handleClick}>Disabled</Button>);

    const button = screen.getByRole('button');
    expect(button).toBeDisabled();
  });

  it('does not trigger click when disabled', async () => {
    const handleClick = vi.fn();
    const user = userEvent.setup();

    render(<Button disabled onClick={handleClick}>Disabled</Button>);

    await user.click(screen.getByRole('button'));

    expect(handleClick).not.toHaveBeenCalled();
  });

  describe('variants', () => {
    it('renders primary variant', () => {
      render(<Button variant="primary">Primary</Button>);

      expect(screen.getByRole('button')).toHaveClass('bg-blue-600');
    });

    it('renders secondary variant', () => {
      render(<Button variant="secondary">Secondary</Button>);

      expect(screen.getByRole('button')).toHaveClass('bg-zinc-700');
    });

    it('renders ghost variant', () => {
      render(<Button variant="ghost">Ghost</Button>);

      expect(screen.getByRole('button')).toHaveClass('hover:bg-zinc-800');
    });

    it('renders danger variant', () => {
      render(<Button variant="danger">Danger</Button>);

      expect(screen.getByRole('button')).toHaveClass('bg-red-600');
    });
  });

  describe('sizes', () => {
    it('renders small size', () => {
      render(<Button size="sm">Small</Button>);

      expect(screen.getByRole('button')).toHaveClass('h-8');
    });

    it('renders medium size', () => {
      render(<Button size="md">Medium</Button>);

      expect(screen.getByRole('button')).toHaveClass('h-10');
    });

    it('renders large size', () => {
      render(<Button size="lg">Large</Button>);

      expect(screen.getByRole('button')).toHaveClass('h-12');
    });
  });

  it('applies custom className', () => {
    render(<Button className="custom-class">Button</Button>);

    expect(screen.getByRole('button')).toHaveClass('custom-class');
  });

  it('forwards ref', () => {
    const ref = vi.fn();

    render(<Button ref={ref}>Button</Button>);

    expect(ref).toHaveBeenCalled();
  });
});
