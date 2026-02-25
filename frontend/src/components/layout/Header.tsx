import { Moon, Sun, Sparkles } from 'lucide-react';
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
    <header className="flex h-14 items-center justify-between border-b border-zinc-800/80 bg-gradient-to-r from-zinc-900 via-zinc-900 to-zinc-900/95 px-6 backdrop-blur-sm">
      <div className="flex items-center gap-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-violet-600 shadow-lg shadow-blue-500/20">
          <Sparkles className="h-4 w-4 text-white" />
        </div>
        <div className="flex items-center gap-2">
          <h1 className="text-lg font-semibold tracking-tight text-zinc-50">
            Marketing Intelligence
          </h1>
          <span className="text-xs text-zinc-600">|</span>
          <span className="text-xs font-medium text-zinc-500">ADK Studio</span>
        </div>
        <Badge variant="info" className="ml-2 animate-pulse text-[10px]">
          Live
        </Badge>
      </div>

      <div className="flex items-center gap-3">
        <span className="text-xs text-zinc-500">Gemini + Vertex AI</span>
        <Button
          variant="ghost"
          size="sm"
          onClick={toggleTheme}
          aria-label="Toggle theme"
        >
          {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </Button>
      </div>
    </header>
  );
}
