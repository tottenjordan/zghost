import { useState, useRef, useCallback, useEffect } from 'react';
import type { ConnectionState, TranscriptMessage, VoiceSessionConfig, VoiceAction } from './types';

const SAMPLE_RATE = 16000; // Input sample rate for microphone
const PLAYBACK_SAMPLE_RATE = 24000; // Gemini Live API output sample rate

export function useVoiceSession(config: VoiceSessionConfig) {
  const [connectionState, setConnectionState] = useState<ConnectionState>('idle');
  const [transcript, setTranscript] = useState<TranscriptMessage[]>([]);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const recordingContextRef = useRef<AudioContext | null>(null);
  const playbackContextRef = useRef<AudioContext | null>(null);
  const playerNodeRef = useRef<AudioWorkletNode | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const connectionStateRef = useRef<ConnectionState>('idle');
  const isSpeakingRef = useRef(false);

  // Keep connectionStateRef in sync with connectionState
  useEffect(() => {
    connectionStateRef.current = connectionState;
  }, [connectionState]);

  // Initialize recording audio context (16kHz for mic input)
  const initRecordingContext = useCallback(async () => {
    if (!recordingContextRef.current) {
      recordingContextRef.current = new AudioContext({ sampleRate: SAMPLE_RATE });
    }
    if (recordingContextRef.current.state === 'suspended') {
      await recordingContextRef.current.resume();
    }
    return recordingContextRef.current;
  }, []);

  // Initialize playback audio context (24kHz) with AudioWorklet
  const initPlaybackContext = useCallback(async () => {
    if (!playbackContextRef.current) {
      playbackContextRef.current = new AudioContext({ sampleRate: PLAYBACK_SAMPLE_RATE });
      await playbackContextRef.current.audioWorklet.addModule('/pcm-player-processor.js');
      const playerNode = new AudioWorkletNode(playbackContextRef.current, 'pcm-player-processor');
      playerNode.connect(playbackContextRef.current.destination);
      playerNodeRef.current = playerNode;
    }
    if (playbackContextRef.current.state === 'suspended') {
      await playbackContextRef.current.resume();
    }
    return playbackContextRef.current;
  }, []);

  // Convert Float32Array to 16-bit PCM
  const floatTo16BitPCM = useCallback((float32Array: Float32Array): ArrayBuffer => {
    const buffer = new ArrayBuffer(float32Array.length * 2);
    const view = new DataView(buffer);
    for (let i = 0; i < float32Array.length; i++) {
      const s = Math.max(-1, Math.min(1, float32Array[i]));
      view.setInt16(i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    }
    return buffer;
  }, []);

  // Start recording from microphone
  const startRecording = useCallback(async () => {
    try {
      const audioContext = await initRecordingContext();
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: SAMPLE_RATE,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      mediaStreamRef.current = stream;
      const source = audioContext.createMediaStreamSource(stream);
      sourceRef.current = source;

      // Create script processor for audio chunks
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;

      processor.onaudioprocess = (e) => {
        if (wsRef.current?.readyState === WebSocket.OPEN && !isSpeakingRef.current) {
          const inputData = e.inputBuffer.getChannelData(0);
          const pcmData = floatTo16BitPCM(inputData);

          // Send audio data to backend proxy
          const message = {
            mime_type: 'audio/pcm',
            data: btoa(String.fromCharCode(...new Uint8Array(pcmData))),
          };
          wsRef.current.send(JSON.stringify(message));
        }
      };

      source.connect(processor);
      processor.connect(audioContext.destination);

      setConnectionState('listening');
    } catch (err) {
      console.error('Failed to start recording:', err);
      setError('Failed to access microphone');
      setConnectionState('error');
    }
  }, [initRecordingContext, floatTo16BitPCM]);

  // Stop recording
  const stopRecording = useCallback(() => {
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }
    if (sourceRef.current) {
      sourceRef.current.disconnect();
      sourceRef.current = null;
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }
  }, []);

  // Play audio response via AudioWorklet ring buffer
  const playAudio = useCallback(async (audioData: string) => {
    try {
      await initPlaybackContext();

      // Decode base64 PCM data to raw ArrayBuffer
      const binaryString = atob(audioData);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }

      // Post raw Int16 PCM data directly to the AudioWorklet ring buffer
      if (playerNodeRef.current) {
        playerNodeRef.current.port.postMessage(bytes.buffer);
      }

      isSpeakingRef.current = true;
      setConnectionState('speaking');
    } catch (err) {
      console.error('Failed to play audio:', err);
    }
  }, [initPlaybackContext]);

  // Connect to WebSocket
  const connect = useCallback(async () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setConnectionState('connecting');
    setError(null);

    try {
      // Generate session ID
      const sessionId = 'voice-' + Date.now();

      // Connect to backend proxy through Vite proxy
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${wsProtocol}//${window.location.host}/ws/${sessionId}`;

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = async () => {
        console.log('WebSocket connected to backend proxy');
        // Pre-initialize playback context so AudioWorklet is ready
        await initPlaybackContext();
        setConnectionState('connected');
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          // Handle action messages from backend tools
          if (data.type === 'action') {
            config.onAction?.(data as VoiceAction);
            return;
          }

          // Handle errors
          if (data.type === 'error') {
            setError(data.message);
            return;
          }

          // Handle turn complete
          if (data.turn_complete) {
            // Signal end of audio to worklet so it flushes the buffer
            if (playerNodeRef.current) {
              playerNodeRef.current.port.postMessage({ command: 'endOfAudio' });
            }
            isSpeakingRef.current = false;
            setConnectionState('connected');
            return;
          }

          // Handle text from model
          if (data.mime_type === 'text/plain' && data.role === 'model') {
            setTranscript((prev) => [
              ...prev,
              {
                id: `assistant-${Date.now()}`,
                role: 'assistant',
                content: data.data,
                timestamp: Date.now(),
              },
            ]);
          }

          // Handle user transcription
          if (data.mime_type === 'text/plain' && data.role === 'user') {
            setTranscript((prev) => [
              ...prev,
              {
                id: `user-${Date.now()}`,
                role: 'user',
                content: data.data,
                timestamp: Date.now(),
              },
            ]);
          }

          // Handle audio from model
          if (data.mime_type === 'audio/pcm' && data.data) {
            playAudio(data.data);
          }
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err);
        }
      };

      ws.onerror = (err) => {
        console.error('WebSocket error:', err);
        setError('Connection error');
        setConnectionState('error');
      };

      ws.onclose = () => {
        console.log('WebSocket closed');
        stopRecording();
        if (connectionStateRef.current !== 'error') {
          setConnectionState('idle');
        }
      };
    } catch (err) {
      console.error('Failed to connect:', err);
      setError('Failed to connect to voice service');
      setConnectionState('error');
    }
  }, [playAudio, stopRecording, initPlaybackContext]);

  // Disconnect WebSocket
  const disconnect = useCallback(() => {
    stopRecording();
    // Clear the audio worklet buffer
    if (playerNodeRef.current) {
      playerNodeRef.current.port.postMessage({ command: 'clear' });
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setConnectionState('idle');
  }, [stopRecording]);

  // Toggle recording
  const toggleRecording = useCallback(async () => {
    if (connectionState === 'idle' || connectionState === 'error') {
      await connect();
      return;
    }

    if (connectionState === 'listening') {
      stopRecording();
      setConnectionState('connected');
    } else if (connectionState === 'connected') {
      await startRecording();
    }
  }, [connectionState, connect, startRecording, stopRecording]);

  // Add user message to transcript
  const addUserMessage = useCallback((text: string) => {
    setTranscript((prev) => [
      ...prev,
      {
        id: `user-${Date.now()}`,
        role: 'user',
        content: text,
        timestamp: Date.now(),
      },
    ]);
  }, []);

  // Send UI context to the backend voice agent
  const sendContext = useCallback((context: Record<string, any>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ mime_type: 'context_update', data: context }));
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
      if (recordingContextRef.current) {
        recordingContextRef.current.close();
      }
      if (playbackContextRef.current) {
        if (playerNodeRef.current) {
          playerNodeRef.current.disconnect();
          playerNodeRef.current = null;
        }
        playbackContextRef.current.close();
      }
    };
  }, [disconnect]);

  return {
    connectionState,
    transcript,
    error,
    connect,
    disconnect,
    toggleRecording,
    isRecording: connectionState === 'listening',
    isConnected: connectionState !== 'idle' && connectionState !== 'error',
    addUserMessage,
    sendContext,
  };
}
