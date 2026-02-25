import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { cn } from '../../lib/utils';
import type { SearchTrend, YTTrend } from '../../types/trends';

interface SearchTrendCardProps {
  trend: SearchTrend;
  selected: boolean;
  onToggle: () => void;
}

export function SearchTrendCard({ trend, selected, onToggle }: SearchTrendCardProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <Card
      className={cn(
        'cursor-pointer transition-all hover:shadow-lg',
        selected && 'ring-2 ring-blue-500 bg-blue-950/20'
      )}
      onClick={(e) => {
        if ((e.target as HTMLElement).tagName !== 'BUTTON') {
          onToggle();
        }
      }}
    >
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-start gap-3 flex-1">
            <input
              type="checkbox"
              checked={selected}
              onChange={onToggle}
              className="mt-1 h-4 w-4 rounded border-zinc-700 bg-zinc-900 text-blue-600 focus:ring-2 focus:ring-blue-500"
              onClick={(e) => e.stopPropagation()}
            />
            <CardTitle className="text-base leading-tight">{trend.title}</CardTitle>
          </div>
          <Badge variant="info">{trend.formattedTraffic}</Badge>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="space-y-2">
          {trend.relatedQueries && (
            <div className="text-sm text-zinc-400">
              <span className="font-medium">Related: </span>
              {trend.relatedQueries}
            </div>
          )}
          {trend.articles && trend.articles.length > 0 && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                setExpanded(!expanded);
              }}
              className="text-xs text-blue-400 hover:text-blue-300"
            >
              {expanded ? 'Hide' : 'Show'} {trend.articles.length} article
              {trend.articles.length !== 1 ? 's' : ''}
            </button>
          )}
          {expanded && trend.articles && (
            <div className="mt-2 space-y-2 border-t border-zinc-800 pt-2">
              {trend.articles.map((article, idx) => (
                <div key={idx} className="text-xs">
                  <a
                    href={article.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-400 hover:underline font-medium"
                    onClick={(e) => e.stopPropagation()}
                  >
                    {article.title}
                  </a>
                  <div className="text-zinc-500 mt-1">
                    {article.source} · {article.timeAgo}
                  </div>
                  <div className="text-zinc-400 mt-1">{article.snippet}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

interface YTTrendCardProps {
  trend: YTTrend;
  selected: boolean;
  onToggle: () => void;
}

export function YTTrendCard({ trend, selected, onToggle }: YTTrendCardProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <Card
      className={cn(
        'cursor-pointer transition-all hover:shadow-lg',
        selected && 'ring-2 ring-blue-500 bg-blue-950/20'
      )}
      onClick={(e) => {
        if ((e.target as HTMLElement).tagName !== 'BUTTON') {
          onToggle();
        }
      }}
    >
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-start gap-3 flex-1">
            <input
              type="checkbox"
              checked={selected}
              onChange={onToggle}
              className="mt-1 h-4 w-4 rounded border-zinc-700 bg-zinc-900 text-blue-600 focus:ring-2 focus:ring-blue-500"
              onClick={(e) => e.stopPropagation()}
            />
            <CardTitle className="text-base leading-tight">{trend.title}</CardTitle>
          </div>
          <Badge variant="success">#{trend.rank}</Badge>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="space-y-2">
          {trend.thumbnail && (
            <div className="aspect-video w-full overflow-hidden rounded-md bg-zinc-800">
              <img
                src={trend.thumbnail}
                alt={trend.title}
                className="h-full w-full object-cover"
              />
            </div>
          )}
          <div className="flex items-center justify-between text-sm text-zinc-400">
            <span className="font-medium">{trend.channelName}</span>
            <span>{trend.viewCount} views</span>
          </div>
          <div className="text-xs text-zinc-500">{trend.publishedTime}</div>
          {trend.description && (
            <>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setExpanded(!expanded);
                }}
                className="text-xs text-blue-400 hover:text-blue-300"
              >
                {expanded ? 'Hide' : 'Show'} description
              </button>
              {expanded && (
                <div className="mt-2 text-xs text-zinc-400 border-t border-zinc-800 pt-2">
                  {trend.description}
                </div>
              )}
            </>
          )}
          <a
            href={trend.videoUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-block text-xs text-blue-400 hover:underline"
            onClick={(e) => e.stopPropagation()}
          >
            Watch on YouTube →
          </a>
        </div>
      </CardContent>
    </Card>
  );
}
