# Voice Brief Assistant

A frontend-only voice agent component that uses Google's Gemini Live API for real-time voice conversations to help refine marketing campaign briefs.

## Features

- **Real-time voice streaming**: Bidirectional audio streaming via WebSocket
- **Speech-to-text**: Automatic transcription of user speech
- **Text-to-speech**: AI responses delivered via natural voice
- **Audio visualization**: Real-time waveform visualization of audio levels
- **Conversation history**: Complete transcript of the conversation
- **Dual modes**: Standalone page or floating widget

## Architecture

### Components

1. **VoiceBriefAssistant.tsx** - Main UI component with controls and transcript
2. **AudioVisualizer.tsx** - Canvas-based audio waveform visualizer
3. **useVoiceSession.ts** - Custom hook managing WebSocket connection and audio I/O
4. **VoicePage.tsx** - Standalone page wrapper
5. **types.ts** - TypeScript type definitions

### Technology Stack

- **Gemini Live API**: `gemini-2.0-flash-live-001` model via WebSocket
- **Web Audio API**: For audio recording and playback
- **MediaRecorder API**: For microphone access
- **Canvas API**: For audio visualization

## Setup

### 1. Get Gemini API Key

Get your API key from [Google AI Studio](https://aistudio.google.com/app/apikey)

### 2. Configure Environment

Add to `.env`:

```bash
VITE_GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. Browser Permissions

The component requires microphone access. Users will be prompted to allow microphone permissions on first use.

## Usage

### As Floating Widget (on Trends page)

Click the "Voice Brief Assistant" button in the header of the Trends page. The assistant appears as a floating widget in the bottom-right corner.

### As Standalone Page

Navigate to `/voice` to use the assistant in full-page mode.

## How It Works

### Connection Flow

1. User clicks "Connect & Record"
2. WebSocket connection established to Gemini Live API
3. Setup message sent with system instructions
4. Microphone access requested
5. Audio streaming begins

### Audio Processing

**Input (User → Gemini)**:
- Microphone audio captured via `getUserMedia()`
- Audio processed at 16kHz sample rate
- Float32 audio converted to 16-bit PCM
- PCM data base64-encoded and sent via WebSocket

**Output (Gemini → User)**:
- WebSocket messages contain audio responses
- Base64 audio decoded to PCM
- PCM converted to Float32 for playback
- Audio played via Web Audio API

### State Machine

```
idle → connecting → connected → listening → processing → speaking → connected
                                     ↓
                                   error
```

## System Prompt

The assistant uses a specialized system prompt focused on:
- Target audience clarification
- Campaign goals and KPIs
- Brand voice and messaging
- Budget and timeline
- Key messaging pillars
- Competitive landscape

## Customization

### Changing the Voice

Edit `useVoiceSession.ts`:

```typescript
voiceConfig: {
  prebuiltVoiceConfig: {
    voiceName: 'Puck', // Options: Aoede, Puck, Charon, Fenrir, Kore
  },
}
```

### Adjusting Audio Quality

Modify sample rate in `useVoiceSession.ts`:

```typescript
const SAMPLE_RATE = 16000; // Options: 8000, 16000, 24000, 48000
```

### Custom System Prompt

Edit `SYSTEM_PROMPT` in `VoiceBriefAssistant.tsx` to change the assistant's behavior.

## Limitations

- Requires HTTPS in production (for microphone access)
- Browser must support Web Audio API
- API key must be kept secure (consider backend proxy for production)
- Network latency affects response time

## Browser Support

- Chrome/Edge 88+
- Firefox 94+
- Safari 15.4+

## Security Considerations

For production:
- Move API key to backend
- Implement authentication
- Add rate limiting
- Use HTTPS only
- Consider backend WebSocket proxy

## Future Enhancements

- [ ] Save conversation to campaign brief
- [ ] Multi-turn conversation memory
- [ ] Voice activity detection (VAD) for automatic recording
- [ ] Export transcript as PDF
- [ ] Custom wake word
- [ ] Multiple language support
- [ ] Integration with campaign metadata
