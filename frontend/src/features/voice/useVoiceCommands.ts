import { useCallback, useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCampaignStore } from '../../stores/campaignStore';
import type { TranscriptMessage } from './types';

export interface VoiceCommand {
  intent: string;
  params?: Record<string, string>;
  confidence: number;
}

interface CommandPattern {
  pattern: RegExp;
  intent: string;
  params?: Record<string, string>;
  paramCapture?: number;
}

// Command patterns to match against transcript text
const COMMAND_PATTERNS: CommandPattern[] = [
  { pattern: /go\s+to\s+(trends?|trend\s+page)/i, intent: 'navigate', params: { path: '/trends' } },
  { pattern: /go\s+to\s+(orchestration|pipeline|run)/i, intent: 'navigate', params: { path: '/orchestration' } },
  { pattern: /go\s+to\s+(voice|voice\s+page)/i, intent: 'navigate', params: { path: '/voice' } },
  { pattern: /go\s+to\s+(rating|rubric)/i, intent: 'navigate', params: { path: '/rating' } },
  { pattern: /go\s+to\s+(studio|av\s+studio)/i, intent: 'navigate', params: { path: '/studio' } },
  { pattern: /go\s+to\s+(narrative|story)/i, intent: 'navigate', params: { path: '/narrative' } },
  { pattern: /show\s+(me\s+)?results/i, intent: 'navigate', params: { path: '/orchestration', tab: 'results' } },
  { pattern: /show\s+(me\s+)?trends/i, intent: 'navigate', params: { path: '/trends' } },
  { pattern: /start\s+(the\s+)?pipeline/i, intent: 'start_pipeline' },
  { pattern: /run\s+(the\s+)?campaign/i, intent: 'start_pipeline' },
  { pattern: /stop\s+(the\s+)?pipeline/i, intent: 'stop_pipeline' },
  { pattern: /set\s+brand\s+to\s+(.+)/i, intent: 'set_brand', paramCapture: 1 },
  { pattern: /set\s+product\s+to\s+(.+)/i, intent: 'set_product', paramCapture: 1 },
  { pattern: /select\s+trend\s+(.+)/i, intent: 'select_trend', paramCapture: 1 },
];

export function useVoiceCommands(transcript: TranscriptMessage[]) {
  const navigate = useNavigate();
  const { setCampaignConfig, config, setPipelineStatus, pipelineStatus } = useCampaignStore();

  const [lastCommand, setLastCommand] = useState<VoiceCommand | null>(null);
  const [commandHistory, setCommandHistory] = useState<VoiceCommand[]>([]);
  const processedIdsRef = useRef<Set<string>>(new Set());

  const parseCommand = useCallback((text: string): VoiceCommand | null => {
    const normalizedText = text.trim();

    for (const commandPattern of COMMAND_PATTERNS) {
      const match = normalizedText.match(commandPattern.pattern);
      if (match) {
        let params = { ...commandPattern.params };

        // Extract captured parameter if specified
        if (commandPattern.paramCapture && match[commandPattern.paramCapture]) {
          params.value = match[commandPattern.paramCapture].trim();
        }

        return {
          intent: commandPattern.intent,
          params,
          confidence: 0.9, // High confidence for pattern match
        };
      }
    }

    return null;
  }, []);

  const executeCommand = useCallback((command: VoiceCommand) => {
    console.log('Executing voice command:', command);

    switch (command.intent) {
      case 'navigate':
        if (command.params?.path) {
          navigate(command.params.path);
        }
        break;

      case 'start_pipeline':
        if (pipelineStatus === 'idle') {
          setPipelineStatus('running');
        }
        break;

      case 'stop_pipeline':
        if (pipelineStatus === 'running') {
          setPipelineStatus('idle');
        }
        break;

      case 'set_brand':
        if (command.params?.value) {
          setCampaignConfig({
            ...config,
            brand: command.params.value,
          });
        }
        break;

      case 'set_product':
        if (command.params?.value) {
          setCampaignConfig({
            ...config,
            target_product: command.params.value,
          });
        }
        break;

      case 'select_trend':
        // This would require integration with trend selection logic
        console.log('Trend selection via voice:', command.params?.value);
        break;

      default:
        console.warn('Unknown command intent:', command.intent);
    }

    setLastCommand(command);
    setCommandHistory((prev) => [...prev, command]);
  }, [navigate, setCampaignConfig, config, setPipelineStatus, pipelineStatus]);

  // Monitor transcript for new user messages
  useEffect(() => {
    if (transcript.length === 0) return;

    // Get the latest user message
    const latestMessage = transcript[transcript.length - 1];

    // Only process user messages and avoid duplicates
    if (latestMessage.role !== 'user' || processedIdsRef.current.has(latestMessage.id)) {
      return;
    }

    // Mark as processed
    processedIdsRef.current.add(latestMessage.id);

    // Parse for commands
    const command = parseCommand(latestMessage.content);
    if (command) {
      executeCommand(command);
    }
  }, [transcript, parseCommand, executeCommand]);

  return {
    lastCommand,
    executeCommand,
    commandHistory,
    parseCommand,
  };
}
