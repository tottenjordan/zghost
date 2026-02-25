import { useState, useRef, useCallback, useEffect } from 'react';
import type { ConnectionState, TranscriptMessage, VoiceSessionConfig } from './types';

const GEMINI_WS_URL = 'wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent';
const SAMPLE_RATE = 16000;

export function useVoiceSession(config: VoiceSessionConfig) {
  const [connectionState, setConnectionState] = useState<ConnectionState>('idle');
  const [transcript, setTranscript] = useState<TranscriptMessage[]>([]);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);

  // Initialize audio context
  const initAudioContext = useCallback(async () => {
    if (!audioContextRef.current) {
      audioContextRef.current = new AudioContext({ sampleRate: SAMPLE_RATE });
    }
    if (audioContextRef.current.state === 'suspended') {
      await audioContextRef.current.resume();
    }
    return audioContextRef.current;
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
      const audioContext = await initAudioContext();
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
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          const inputData = e.inputBuffer.getChannelData(0);
          const pcmData = floatTo16BitPCM(inputData);

          // Send audio data to Gemini
          const message = {
            realtimeInput: {
              mediaChunks: [
                {
                  mimeType: 'audio/pcm',
                  data: btoa(String.fromCharCode(...new Uint8Array(pcmData))),
                },
              ],
            },
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
  }, [initAudioContext, floatTo16BitPCM]);

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

  // Play audio response
  const playAudio = useCallback(async (audioData: string) => {
    try {
      const audioContext = await initAudioContext();

      // Decode base64 PCM data
      const binaryString = atob(audioData);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }

      // Convert PCM to Float32Array
      const int16Array = new Int16Array(bytes.buffer);
      const float32Array = new Float32Array(int16Array.length);
      for (let i = 0; i < int16Array.length; i++) {
        float32Array[i] = int16Array[i] / 0x8000;
      }

      // Create audio buffer
      const audioBuffer = audioContext.createBuffer(1, float32Array.length, SAMPLE_RATE);
      audioBuffer.getChannelData(0).set(float32Array);

      // Play audio
      const source = audioContext.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(audioContext.destination);

      setConnectionState('speaking');

      source.onended = () => {
        setConnectionState('connected');
      };

      source.start(0);
    } catch (err) {
      console.error('Failed to play audio:', err);
    }
  }, [initAudioContext]);

  // Connect to WebSocket
  const connect = useCallback(async () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setConnectionState('connecting');
    setError(null);

    try {
      const ws = new WebSocket(`${GEMINI_WS_URL}?key=${config.apiKey}`);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('WebSocket connected');

        // Send setup message with system instructions
        const setupMessage = {
          setup: {
            model: 'models/gemini-2.0-flash-live-001',
            systemInstruction: {
              parts: [{ text: config.systemPrompt }],
            },
            generationConfig: {
              responseModalities: 'audio',
              speechConfig: {
                voiceConfig: {
                  prebuiltVoiceConfig: {
                    voiceName: 'Aoede',
                  },
                },
              },
            },
          },
        };

        ws.send(JSON.stringify(setupMessage));
        setConnectionState('connected');
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          // Handle setup complete
          if (data.setupComplete) {
            console.log('Setup complete');
            return;
          }

          // Handle server content (audio response)
          if (data.serverContent?.modelTurn?.parts) {
            const parts = data.serverContent.modelTurn.parts;

            // Handle text transcript
            const textPart = parts.find((p: { text?: string }) => p.text);
            if (textPart?.text) {
              setTranscript((prev) => [
                ...prev,
                {
                  id: `assistant-${Date.now()}`,
                  role: 'assistant',
                  content: textPart.text,
                  timestamp: Date.now(),
                },
              ]);
            }

            // Handle audio
            const audioPart = parts.find((p: { inlineData?: { data: string; mimeType?: string } }) =>
              p.inlineData?.mimeType?.startsWith('audio/')
            );
            if (audioPart?.inlineData?.data) {
              playAudio(audioPart.inlineData.data);
            }
          }

          // Handle turn complete
          if (data.serverContent?.turnComplete) {
            setConnectionState('connected');
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
        if (connectionState !== 'error') {
          setConnectionState('idle');
        }
      };
    } catch (err) {
      console.error('Failed to connect:', err);
      setError('Failed to connect to voice service');
      setConnectionState('error');
    }
  }, [config.apiKey, config.systemPrompt, connectionState, playAudio, stopRecording]);

  // Disconnect WebSocket
  const disconnect = useCallback(() => {
    stopRecording();
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

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
      if (audioContextRef.current) {
        audioContextRef.current.close();
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
  };
}
