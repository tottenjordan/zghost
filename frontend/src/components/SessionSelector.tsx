import { useState, useEffect } from 'react';
import { ChevronDown, Plus, Clock, Check } from 'lucide-react';

interface Session {
  id: string;
  createdAt?: string;
  lastModified?: string;
  messageCount?: number;
}

interface SessionSelectorProps {
  currentSessionId: string | null;
  userId: string | null;
  appName: string | null;
  onSessionChange: (sessionId: string) => void;
}

export function SessionSelector({ currentSessionId, userId, appName, onSessionChange }: SessionSelectorProps) {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (userId && appName) {
      fetchSessions();
    }
  }, [userId, appName]);

  const fetchSessions = async () => {
    if (!userId || !appName) {
      console.log('[SessionSelector] Missing userId or appName:', { userId, appName });
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const url = `/api/apps/${appName}/users/${userId}/sessions`;
      console.log('[SessionSelector] Fetching sessions from:', url);
      const response = await fetch(url);
      
      if (response.ok) {
        const data = await response.json();
        // Transform the API response to our Session format
        console.log('[SessionSelector] Raw sessions data:', data);
        const transformedSessions: Session[] = data.map((session: any) => ({
          id: session.id || session.session_id,
          createdAt: new Date(session.lastUpdateTime * 1000).toISOString(),
          lastModified: new Date(session.lastUpdateTime * 1000).toISOString(),
          messageCount: session.events?.length || 0
        }));
        console.log('[SessionSelector] Transformed sessions:', transformedSessions);
        setSessions(transformedSessions);
      } else {
        // Fallback to current session only
        const currentSessionData: Session[] = currentSessionId ? [{
          id: currentSessionId,
          createdAt: new Date().toISOString(),
          messageCount: 0
        }] : [];
        setSessions(currentSessionData);
      }
    } catch (err) {
      console.error('Error fetching sessions:', err);
      // Use current session as fallback
      setSessions([
        { 
          id: currentSessionId || 'current-session',
          createdAt: new Date().toISOString(),
          messageCount: 0
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const createNewSession = () => {
    const newSessionId = `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    onSessionChange(newSessionId);
    setIsOpen(false);
  };

  const formatSessionName = (session: Session) => {
    if (session.id === currentSessionId) {
      return 'Current Session';
    }
    
    // Show the full session ID for test sessions
    if (session.id.startsWith('test-')) {
      return session.id;
    }
    
    // For other sessions, show a truncated version
    return session.id.length > 30 ? session.id.substring(0, 30) + '...' : session.id;
  };

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 bg-neutral-800 hover:bg-neutral-700 border border-neutral-700 rounded-lg transition-colors text-sm"
      >
        <Clock className="h-4 w-4 text-neutral-400" />
        <span className="text-neutral-200">
          {currentSessionId ? formatSessionName({ id: currentSessionId }) : 'Select Session'}
        </span>
        <ChevronDown className={`h-4 w-4 text-neutral-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="absolute top-full mt-2 right-0 w-64 bg-neutral-800 border border-neutral-700 rounded-lg shadow-xl z-50">
          <div className="p-2">
            <button
              onClick={createNewSession}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm text-neutral-200 hover:bg-neutral-700 rounded-lg transition-colors"
            >
              <Plus className="h-4 w-4" />
              <span>New Session</span>
            </button>
          </div>
          
          <div className="border-t border-neutral-700">
            <div className="max-h-64 overflow-y-auto">
              {loading ? (
                <div className="p-4 text-center text-neutral-400 text-sm">
                  Loading sessions...
                </div>
              ) : sessions.length === 0 ? (
                <div className="p-4 text-center text-neutral-400 text-sm">
                  No sessions found
                </div>
              ) : (
                <div className="p-2 space-y-1">
                  {sessions.map((session) => (
                    <button
                      key={session.id}
                      onClick={() => {
                        onSessionChange(session.id);
                        setIsOpen(false);
                      }}
                      className={`w-full flex items-center justify-between px-3 py-2 text-sm rounded-lg transition-colors ${
                        session.id === currentSessionId
                          ? 'bg-neutral-700 text-neutral-100'
                          : 'text-neutral-300 hover:bg-neutral-700'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <Clock className="h-3 w-3 text-neutral-400" />
                        <span>{formatSessionName(session)}</span>
                      </div>
                      {session.id === currentSessionId && (
                        <Check className="h-4 w-4 text-green-400" />
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Click outside to close */}
      {isOpen && (
        <div 
          className="fixed inset-0 z-40" 
          onClick={() => setIsOpen(false)}
        />
      )}
    </div>
  );
}