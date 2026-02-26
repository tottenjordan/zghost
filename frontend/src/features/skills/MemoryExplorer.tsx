import { useState, useEffect, useCallback } from 'react';
import { Search, Database, Clock, AlertCircle, Loader2, Plus, Zap, Trash2, CheckCircle2, XCircle } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';

interface MemoryEntry {
  id: string;
  fact: string;
  scope: { user_id?: string };
  update_time: string;
  distance?: number;
}

interface MemoryApiResponse {
  memories: MemoryEntry[];
  source: string;
  count?: number;
  message?: string;
}

interface HealthResponse {
  configured: boolean;
  connected: boolean;
  engine_id?: string;
  error?: string;
}

const CAMPAIGN_SEED_FACTS = [
  'User ran a Google Pixel 9 Pro campaign targeting tech-savvy millennials with AI camera and Tensor G4 chip',
  'McDonalds McRib campaign produced a research report, 3 ad creative variants, and a 30-second commercial',
  'User typically selects 2-3 YouTube trends and 1-2 Google Search trends for campaign research',
  'Nike Air Max campaign produced a 30-second commercial video stored in GCS',
  'User prefers concise ad copy with emotional hooks and clear CTAs for Gen Z audiences',
];

export function MemoryExplorer() {
  const [memories, setMemories] = useState<MemoryEntry[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [source, setSource] = useState<string>('loading');
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [newFact, setNewFact] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [isPopulating, setIsPopulating] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);

  // Check health on mount
  useEffect(() => {
    fetch('/api/memories/health')
      .then((r) => r.json())
      .then(setHealth)
      .catch(() => setHealth({ configured: false, connected: false }));
  }, []);

  const fetchMemories = useCallback(async (query = '') => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams({ user_id: 'frontend-user' });
      if (query) params.set('query', query);

      const res = await fetch(`/api/memories?${params}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const data: MemoryApiResponse = await res.json();
      setSource(data.source);

      if (data.source === 'memory_bank') {
        setMemories(data.memories);
        setStatusMessage(data.memories.length === 0
          ? (query ? 'No memories match your search.' : 'No memories yet. Create one or populate demo data.')
          : null);
      } else if (data.source === 'not_configured') {
        setMemories([]);
        setStatusMessage('Memory Bank not configured. Set MEMORY_BANK_AGENT_ENGINE_ID env var.');
      } else if (data.source === 'error') {
        setMemories([]);
        setStatusMessage(data.message || 'Memory Bank error.');
      } else {
        setMemories(data.memories);
        setStatusMessage(data.message || null);
      }
    } catch (err) {
      console.error('Failed to fetch memories:', err);
      setMemories([]);
      setSource('error');
      setStatusMessage('Could not reach Memory Bank API. Is the memory server running?');
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Initial fetch
  useEffect(() => {
    fetchMemories();
  }, [fetchMemories]);

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => {
      fetchMemories(searchQuery);
    }, 400);
    return () => clearTimeout(timer);
  }, [searchQuery, fetchMemories]);

  const createMemory = async () => {
    if (!newFact.trim()) return;
    setIsCreating(true);
    try {
      const res = await fetch('/api/memories', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fact: newFact.trim(), user_id: 'frontend-user' }),
      });
      const data = await res.json();
      if (data.error) {
        setStatusMessage(`Create failed: ${data.error}`);
      } else {
        setNewFact('');
        setShowCreateForm(false);
        // Refresh after a short delay for Memory Bank to index
        setTimeout(() => fetchMemories(searchQuery), 1000);
      }
    } catch (err) {
      setStatusMessage('Failed to create memory.');
    } finally {
      setIsCreating(false);
    }
  };

  const populateDemoMemories = async () => {
    setIsPopulating(true);
    try {
      const res = await fetch('/api/memories/populate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: 'frontend-user', facts: CAMPAIGN_SEED_FACTS }),
      });
      const data = await res.json();
      if (data.error) {
        setStatusMessage(`Populate failed: ${data.error}`);
      } else {
        setStatusMessage(`Populated ${data.populated} memories.`);
        setTimeout(() => fetchMemories(searchQuery), 1500);
      }
    } catch (err) {
      setStatusMessage('Failed to populate memories.');
    } finally {
      setIsPopulating(false);
    }
  };

  const purgeMemories = async () => {
    if (!confirm('Delete all memories for this user?')) return;
    try {
      await fetch('/api/memories?user_id=frontend-user', { method: 'DELETE' });
      setMemories([]);
      setStatusMessage('All memories purged.');
      setTimeout(() => fetchMemories(), 500);
    } catch {
      setStatusMessage('Failed to purge memories.');
    }
  };

  const isConnected = health?.connected === true;
  const isConfigured = health?.configured === true;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Database className="h-4 w-4" />
              Memory Bank
            </CardTitle>
            <div className="flex items-center gap-2">
              {/* Connection indicator */}
              {health && (
                <span className="flex items-center gap-1">
                  {isConnected ? (
                    <CheckCircle2 className="h-3 w-3 text-emerald-500" />
                  ) : isConfigured ? (
                    <AlertCircle className="h-3 w-3 text-amber-500" />
                  ) : (
                    <XCircle className="h-3 w-3 text-red-500" />
                  )}
                  <span className="text-[10px] text-zinc-500">
                    {isConnected ? 'Connected' : isConfigured ? 'Configured' : 'Not configured'}
                  </span>
                </span>
              )}
              <span className="text-xs text-zinc-500">
                {isLoading ? '...' : `${memories.length} entries`}
              </span>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {statusMessage && (
            <div className="mb-4 flex items-start gap-2 rounded-lg border border-amber-800/50 bg-amber-950/20 px-3 py-2">
              <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-500" />
              <p className="text-xs text-amber-400">{statusMessage}</p>
            </div>
          )}

          {/* Search bar */}
          <div className="relative mb-4">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
            <input
              type="text"
              placeholder="Search memories by content..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-lg border border-zinc-700 bg-zinc-800 py-2 pl-10 pr-4 text-sm text-zinc-200 placeholder:text-zinc-500 focus:border-blue-600 focus:outline-none focus:ring-1 focus:ring-blue-600"
            />
          </div>

          {/* Action buttons */}
          <div className="mb-4 flex flex-wrap gap-2">
            <button
              onClick={() => setShowCreateForm(!showCreateForm)}
              className="flex items-center gap-1.5 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-1.5 text-xs text-zinc-300 transition-colors hover:border-blue-600 hover:text-blue-400"
            >
              <Plus className="h-3 w-3" />
              Create Memory
            </button>
            <button
              onClick={populateDemoMemories}
              disabled={isPopulating}
              className="flex items-center gap-1.5 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-1.5 text-xs text-zinc-300 transition-colors hover:border-emerald-600 hover:text-emerald-400 disabled:opacity-50"
            >
              {isPopulating ? <Loader2 className="h-3 w-3 animate-spin" /> : <Zap className="h-3 w-3" />}
              Populate Demo
            </button>
            {memories.length > 0 && (
              <button
                onClick={purgeMemories}
                className="flex items-center gap-1.5 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-1.5 text-xs text-zinc-300 transition-colors hover:border-red-600 hover:text-red-400"
              >
                <Trash2 className="h-3 w-3" />
                Purge All
              </button>
            )}
          </div>

          {/* Create form */}
          {showCreateForm && (
            <div className="mb-4 rounded-lg border border-zinc-700 bg-zinc-800/50 p-3">
              <textarea
                value={newFact}
                onChange={(e) => setNewFact(e.target.value)}
                placeholder="Enter a memory fact (e.g., 'User prefers 30-second commercials with energetic music')"
                rows={2}
                className="w-full rounded-lg border border-zinc-700 bg-zinc-900 p-2 text-sm text-zinc-200 placeholder:text-zinc-500 focus:border-blue-600 focus:outline-none focus:ring-1 focus:ring-blue-600"
              />
              <div className="mt-2 flex justify-end gap-2">
                <button
                  onClick={() => { setShowCreateForm(false); setNewFact(''); }}
                  className="rounded px-3 py-1 text-xs text-zinc-400 hover:text-zinc-200"
                >
                  Cancel
                </button>
                <button
                  onClick={createMemory}
                  disabled={!newFact.trim() || isCreating}
                  className="flex items-center gap-1 rounded bg-blue-600 px-3 py-1 text-xs font-medium text-white hover:bg-blue-500 disabled:opacity-50"
                >
                  {isCreating ? <Loader2 className="h-3 w-3 animate-spin" /> : <Plus className="h-3 w-3" />}
                  Save
                </button>
              </div>
            </div>
          )}

          {/* Memory list */}
          <div className="space-y-3">
            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-5 w-5 animate-spin text-zinc-500" />
                <span className="ml-2 text-sm text-zinc-500">Loading memories...</span>
              </div>
            ) : memories.length === 0 ? (
              <p className="py-8 text-center text-sm text-zinc-500">No memories found</p>
            ) : (
              memories.map((entry) => (
                <div
                  key={entry.id}
                  className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-3 transition-colors hover:border-zinc-700"
                >
                  <div className="mb-2 flex items-center justify-between">
                    <span className="text-xs font-mono text-zinc-500">
                      {entry.scope?.user_id || 'unknown'}
                    </span>
                    <div className="flex items-center gap-2">
                      {entry.distance !== undefined && (
                        <span className="text-[10px] text-blue-400">
                          relevance: {(entry.distance * 100).toFixed(0)}%
                        </span>
                      )}
                      <span className="flex items-center gap-1 text-[10px] text-zinc-600">
                        <Clock className="h-3 w-3" />
                        {entry.update_time
                          ? new Date(entry.update_time).toLocaleDateString()
                          : 'N/A'}
                      </span>
                    </div>
                  </div>
                  <p className="text-sm text-zinc-300">{entry.fact}</p>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
