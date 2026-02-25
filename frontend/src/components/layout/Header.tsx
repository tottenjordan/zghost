import { Moon, Sun } from 'lucide-react';
import { useState } from 'react';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';

export function Header() {
  const [isDark, setIsDark] = useState(true);

  const toggleTheme = () => {
    setIsDark(!isDark);
    document.documentElement.classList.toggle('dark');
  };

  return (
    <header className="flex h-16 items-center justify-between border-b border-zinc-800 bg-zinc-900 px-6">
      <div className="flex items-center gap-4">
        <h1 className="text-xl font-bold text-zinc-50">Marketing Intelligence</h1>
        <Badge variant="info">Session Active</Badge>
      </div>

      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="sm"
          onClick={toggleTheme}
          aria-label="Toggle theme"
        >
          {isDark ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
        </Button>
      </div>
    </header>
  );
}
