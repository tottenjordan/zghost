import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '../test-utils';
import userEvent from '@testing-library/user-event';
import { Input } from '../../components/ui/Input';

describe('Input', () => {
  it('renders with default type text', () => {
    render(<Input />);

    const input = screen.getByRole('textbox');
    expect(input).toHaveAttribute('type', 'text');
  });

  it('renders with specified type', () => {
    render(<Input type="email" />);

    const input = screen.getByRole('textbox');
    expect(input).toHaveAttribute('type', 'email');
  });

  it('handles value changes', async () => {
    const handleChange = vi.fn();
    const user = userEvent.setup();

    render(<Input onChange={handleChange} />);

    const input = screen.getByRole('textbox');
    await user.type(input, 'test');

    expect(handleChange).toHaveBeenCalled();
  });

  it('displays placeholder text', () => {
    render(<Input placeholder="Enter text" />);

    expect(screen.getByPlaceholderText('Enter text')).toBeInTheDocument();
  });

  it('renders disabled state', () => {
    render(<Input disabled />);

    expect(screen.getByRole('textbox')).toBeDisabled();
  });

  it('applies disabled styling', () => {
    render(<Input disabled />);

    expect(screen.getByRole('textbox')).toHaveClass('disabled:cursor-not-allowed', 'disabled:opacity-50');
  });

  it('displays value', () => {
    render(<Input value="test value" onChange={vi.fn()} />);

    expect(screen.getByRole('textbox')).toHaveValue('test value');
  });

  it('applies custom className', () => {
    render(<Input className="custom-class" />);

    expect(screen.getByRole('textbox')).toHaveClass('custom-class');
  });

  it('applies default styling', () => {
    render(<Input />);

    expect(screen.getByRole('textbox')).toHaveClass('rounded-md', 'border', 'bg-zinc-900');
  });

  it('forwards ref', () => {
    const ref = vi.fn();

    render(<Input ref={ref} />);

    expect(ref).toHaveBeenCalled();
  });

  it('supports controlled input', async () => {
    const user = userEvent.setup();
    let value = '';
    const handleChange = vi.fn((e) => {
      value = e.target.value;
    });

    const { rerender } = render(<Input value={value} onChange={handleChange} />);

    const input = screen.getByRole('textbox');
    await user.type(input, 'new');

    expect(handleChange).toHaveBeenCalled();
  });
});
