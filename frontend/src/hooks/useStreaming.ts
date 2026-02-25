import { useEffect, useState } from 'react';
import { createEventStream } from '../services/streaming';
import type { AgentEvent } from '../types/agents';

export function useStreaming(streamUrl: string | null) {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<Event | null>(null);

  useEffect(() => {
    if (!streamUrl) {
      setIsConnected(false);
      return;
    }

    setIsConnected(true);
    const cleanup = createEventStream(
      streamUrl,
      (event) => {
        setEvents((prev) => [...prev, event]);
      },
      (err) => {
        setError(err);
        setIsConnected(false);
      }
    );

    return cleanup;
  }, [streamUrl]);

  const clearEvents = () => setEvents([]);

  return {
    events,
    isConnected,
    error,
    clearEvents,
  };
}
