import { useEffect, useState, useRef } from 'react';
import { createEventStream } from '../services/streaming';
import type { AgentEvent } from '../types/agents';

export function useStreaming(streamUrl: string | null) {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<Event | null>(null);
  const cleanupRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    if (!streamUrl) {
      setIsConnected(false);
      return;
    }

    // Close previous stream if any
    cleanupRef.current?.();

    setIsConnected(true);
    // Accumulate events across streams (don't reset)
    const cleanup = createEventStream(
      streamUrl,
      (event) => {
        setEvents((prev) => [...prev, event]);
      },
      (err) => {
        setError(err);
        setIsConnected(false);
      },
      () => {
        // Stream completed — mark disconnected but keep events
        setIsConnected(false);
      }
    );
    cleanupRef.current = cleanup;

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
