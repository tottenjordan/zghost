import { useEffect, useState } from 'react';
import { CheckCircle2, Command } from 'lucide-react';
import { useVoiceCommands } from './useVoiceCommands';
import type { TranscriptMessage } from './types';
import type { VoiceCommand } from './useVoiceCommands';
import { cn } from '../../lib/utils';

interface VoiceCommandRouterProps {
  transcript: TranscriptMessage[];
  onCommandExecuted?: (command: VoiceCommand) => void;
}

export function VoiceCommandRouter({ transcript, onCommandExecuted }: VoiceCommandRouterProps) {
  const { lastCommand } = useVoiceCommands(transcript);
  const [showNotification, setShowNotification] = useState(false);
  const [notificationMessage, setNotificationMessage] = useState('');

  useEffect(() => {
    if (lastCommand) {
      // Generate human-readable notification
      const message = getCommandMessage(lastCommand);
      setNotificationMessage(message);
      setShowNotification(true);

      // Auto-hide after 3 seconds
      const timer = setTimeout(() => {
        setShowNotification(false);
      }, 3000);

      // Notify parent if callback provided
      onCommandExecuted?.(lastCommand);

      return () => clearTimeout(timer);
    }
  }, [lastCommand, onCommandExecuted]);

  if (!showNotification) return null;

  return (
    <div className="fixed top-4 right-4 z-50 animate-in slide-in-from-top-2 fade-in duration-300">
      <div className="flex items-center gap-3 rounded-lg border border-blue-700 bg-blue-950/90 px-4 py-3 shadow-lg backdrop-blur-sm">
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-600/20">
          <Command className="h-4 w-4 text-blue-400" />
        </div>
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-green-400" />
            <span className="text-sm font-medium text-zinc-100">Command Executed</span>
          </div>
          <span className="text-xs text-zinc-400">{notificationMessage}</span>
        </div>
      </div>
    </div>
  );
}

function getCommandMessage(command: VoiceCommand): string {
  switch (command.intent) {
    case 'navigate':
      return `Navigating to ${getPageName(command.params?.path)}`;
    case 'start_pipeline':
      return 'Starting campaign pipeline...';
    case 'stop_pipeline':
      return 'Stopping pipeline...';
    case 'set_brand':
      return `Setting brand to "${command.params?.value}"`;
    case 'set_product':
      return `Setting product to "${command.params?.value}"`;
    case 'select_trend':
      return `Selecting trend: ${command.params?.value}`;
    default:
      return 'Command executed';
  }
}

function getPageName(path?: string): string {
  switch (path) {
    case '/trends':
      return 'Trends';
    case '/orchestration':
      return 'Orchestration';
    case '/voice':
      return 'Voice';
    case '/rating':
      return 'Rating';
    case '/studio':
      return 'Studio';
    case '/narrative':
      return 'Narrative';
    default:
      return path || 'page';
  }
}
