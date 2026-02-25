import { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { ChevronDown, ChevronRight, Sparkles } from 'lucide-react';
import { cn } from '../../lib/utils';

interface SessionStatePanelProps {
  state: Record<string, any>;
  changedKeys: Set<string>;
}

function truncateValue(value: any, maxLength = 100): string {
  const str = typeof value === 'string' ? value : JSON.stringify(value);
  if (str.length > maxLength) {
    return str.slice(0, maxLength) + '...';
  }
  return str;
}

function StateKeyRow({
  stateKey,
  value,
  isChanged,
}: {
  stateKey: string;
  value: any;
  isChanged: boolean;
}) {
  const [isExpanded, setIsExpanded] = useState(false);
  const hasNestedValue = typeof value === 'object' && value !== null;

  return (
    <div
      className={cn(
        'border border-zinc-800 rounded p-2 transition-colors',
        isChanged && 'bg-blue-950/30 border-blue-800/50'
      )}
    >
      <div className="flex items-start gap-2">
        {hasNestedValue && (
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-zinc-400 hover:text-zinc-200 flex-shrink-0"
          >
            {isExpanded ? (
              <ChevronDown className="w-4 h-4" />
            ) : (
              <ChevronRight className="w-4 h-4" />
            )}
          </button>
        )}

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-mono text-sm text-blue-400 font-semibold">
              {stateKey}
            </span>
            {isChanged && (
              <Sparkles className="w-3 h-3 text-blue-400" />
            )}
          </div>

          {!isExpanded && (
            <div className="font-mono text-xs text-zinc-400 mt-1 truncate">
              {truncateValue(value)}
            </div>
          )}

          {isExpanded && (
            <pre className="font-mono text-xs text-zinc-400 mt-2 overflow-x-auto bg-zinc-950 p-2 rounded border border-zinc-800">
              {JSON.stringify(value, null, 2)}
            </pre>
          )}
        </div>

        <Badge variant="default" className="text-xs flex-shrink-0">
          {typeof value}
        </Badge>
      </div>
    </div>
  );
}

export function SessionStatePanel({ state, changedKeys }: SessionStatePanelProps) {
  const stateKeys = Object.keys(state).sort();
  const changedCount = changedKeys.size;

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="flex-shrink-0">
        <CardTitle className="text-base flex items-center justify-between">
          <span>Session State</span>
          {changedCount > 0 && (
            <Badge variant="info" className="text-xs">
              {changedCount} changed
            </Badge>
          )}
        </CardTitle>
        <p className="text-xs text-zinc-400 mt-1">
          {stateKeys.length} keys in session state
        </p>
      </CardHeader>

      <CardContent className="flex-1 overflow-y-auto space-y-2">
        {stateKeys.length === 0 ? (
          <div className="text-center text-zinc-500 py-8">
            No state keys yet. Start the pipeline to populate state.
          </div>
        ) : (
          stateKeys.map((key) => (
            <StateKeyRow
              key={key}
              stateKey={key}
              value={state[key]}
              isChanged={changedKeys.has(key)}
            />
          ))
        )}
      </CardContent>
    </Card>
  );
}
