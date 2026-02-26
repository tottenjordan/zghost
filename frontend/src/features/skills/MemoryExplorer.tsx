import { useState } from 'react';
import { Search, Database, Clock } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';

interface MemoryEntry {
  id: string;
  sessionId: string;
  timestamp: string;
  keys: string[];
  summary: string;
}

// Demo data - in production would fetch from API
const DEMO_MEMORIES: MemoryEntry[] = [
  {
    id: 'mem-1',
    sessionId: 'session-pixel-001',
    timestamp: '2026-02-25T10:30:00Z',
    keys: ['brand', 'target_product', 'target_search_trends'],
    summary: 'Google Pixel 9 Pro campaign setup with 3 search trends selected',
  },
  {
    id: 'mem-2',
    sessionId: 'session-mcrib-001',
    timestamp: '2026-02-24T14:15:00Z',
    keys: ['brand', 'combined_final_cited_report', 'final_select_ad_copies'],
    summary: "McDonald's McRib campaign with completed research report and ad copies",
  },
  {
    id: 'mem-3',
    sessionId: 'session-nike-001',
    timestamp: '2026-02-23T09:00:00Z',
    keys: ['brand', 'target_audience', 'commercial_video_url'],
    summary: 'Nike Air Max campaign with finished commercial video',
  },
];

export function MemoryExplorer() {
  const [searchQuery, setSearchQuery] = useState('');

  const filtered = DEMO_MEMORIES.filter(m =>
    m.summary.toLowerCase().includes(searchQuery.toLowerCase()) ||
    m.sessionId.toLowerCase().includes(searchQuery.toLowerCase()) ||
    m.keys.some(k => k.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Database className="h-4 w-4" />
              Memory Bank
            </CardTitle>
            <span className="text-xs text-zinc-500">{filtered.length} entries</span>
          </div>
        </CardHeader>
        <CardContent>
          <div className="relative mb-4">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
            <input
              type="text"
              placeholder="Search memories by session, key, or content..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-lg border border-zinc-700 bg-zinc-800 py-2 pl-10 pr-4 text-sm text-zinc-200 placeholder:text-zinc-500 focus:border-blue-600 focus:outline-none focus:ring-1 focus:ring-blue-600"
            />
          </div>

          <div className="space-y-3">
            {filtered.length === 0 ? (
              <p className="py-8 text-center text-sm text-zinc-500">No memories found</p>
            ) : (
              filtered.map((entry) => (
                <div
                  key={entry.id}
                  className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-3 transition-colors hover:border-zinc-700"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-mono text-zinc-500">{entry.sessionId}</span>
                    <span className="flex items-center gap-1 text-[10px] text-zinc-600">
                      <Clock className="h-3 w-3" />
                      {new Date(entry.timestamp).toLocaleDateString()}
                    </span>
                  </div>
                  <p className="text-sm text-zinc-300 mb-2">{entry.summary}</p>
                  <div className="flex flex-wrap gap-1">
                    {entry.keys.map(key => (
                      <span key={key} className="rounded bg-zinc-800 px-1.5 py-0.5 text-[10px] text-zinc-400">
                        {key}
                      </span>
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
