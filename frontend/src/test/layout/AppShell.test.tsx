import { describe, it, expect } from 'vitest';
import { render, screen } from '../test-utils';
import { AppShell } from '../../components/layout/AppShell';

describe('AppShell', () => {
  it('renders header component', () => {
    render(<AppShell />);

    // Header should be present (would check for specific header content)
    const header = document.querySelector('header');
    expect(header).toBeInTheDocument();
  });

  it('renders sidebar component', () => {
    render(<AppShell />);

    // Sidebar should be present (would check for specific nav elements)
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
});
