# PRD: Dictation Support and Voice Mode

**GitHub Issue**: [#160](https://github.com/jeremysball/alfred/issues/160)  
**Priority**: High  
**Status**: Draft  
**Created**: 2026-03-26

---

## Problem

Users need:
1. **Hands-free operation** while multitasking (coding, cooking, commuting hands)
2. **Accessibility support** for users with motor impairments or repetitive strain injuries
3. **Faster long-form input**—speaking is 3x faster than typing
4. **Natural conversation flow**—voice feels more personal for AI assistants

Current text-only interface limits convenience and excludes users who prefer or need voice interaction.

---

## Solution

Add bidirectional voice support to Alfred's Web UI:

- **Speech-to-Text (STT)**: Users speak, text appears in chat input in real-time
- **Text-to-Speech (TTS)**: AI responses are spoken aloud automatically or on-demand
- **Dual backend support**: Local Whisper (privacy-first) + Cloud Whisper API (convenience)
- **Production UX**: Sub-500ms latency, high accuracy, graceful fallbacks

---

## User Experience

### Voice Input Flow

```
[User clicks 🎤 button in chat input]
        ↓
[UI shows "Listening..." animation]
        ↓
[Real-time transcription streams into input field]
        ↓
[User stops speaking → auto-submit OR manual submit]
        ↓
[AI response streams in]
        ↓
[TTS reads response aloud (if enabled)]
```

### UI Components

**1. Voice Input Button**
- Located in chat input bar (right side, next to send button)
- States: Idle (🎤), Listening (animated 🎙️), Processing (⏳), Error (⚠️)
- Keyboard shortcut: `Ctrl+Shift+V` (or `Cmd+Shift+V` on Mac)

**2. Real-time Transcription Display**
- Streams live text into the input field as user speaks
- Shows confidence indicators (low-confidence words underlined)
- Interim results (gray) → Final results (black)

**3. Voice Settings Panel**
- STT provider selector (Local / Cloud)
- TTS voice selector (multiple voices per provider)
- Auto-read responses toggle
- Voice activity detection sensitivity

**4. Audio Feedback**
- Earcon (soft sound) on voice activation
- Earcon on transcription complete
- Visual waveforms during recording

### TTS (Text-to-Speech) Flow

**Option A: Auto-read**
- Every AI response is spoken automatically after streaming completes
- Mute button in message header to silence individual messages
- Global "mute all" toggle in settings

**Option B: On-demand play**
- Play button (🔊) appears on each AI message
- Click to hear that specific message
- Natural for mixed voice/text workflows

---

## Technical Architecture

### Backend Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Web UI (React/JS)                       │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐     │
│  │ Audio Capture│  │ Transcription│  │  TTS Playback   │     │
│  │  (WebRTC)   │  │  (WebSocket) │  │  (Audio API)    │     │
│  └──────┬──────┘  └──────┬───────┘  └────────┬────────┘     │
└─────────┼────────────────┼───────────────────┼──────────────┘
          │                │                   │
          ▼                ▼                   ▼
┌─────────────────────────────────────────────────────────────┐
│                      Alfred Server (Python)                 │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Voice Router (FastAPI)                 │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌───────────┐  │    │
│  │  │ STT Handler  │  │ TTS Handler  │  │ Config    │  │    │
│  │  └──────┬───────┘  └──────┬───────┘  └───────────┘  │    │
│  └─────────┼─────────────────┼──────────────────────────┘    │
└────────────┼─────────────────┼───────────────────────────────┘
             │                 │
    ┌────────┴────────┐   ┌────┴────────────┐
    │   LOCAL MODE    │   │   CLOUD MODE    │
    │  ┌───────────┐  │   │  ┌───────────┐  │
    │  │ Whisper   │  │   │  │ Whisper   │  │
    │  │ (local)   │  │   │  │ API       │  │
    │  └───────────┘  │   │  └───────────┘  │
    │  ┌───────────┐  │   │  ┌───────────┐  │
    │  │ Piper/    │  │   │  │ ElevenLabs│  │
    │  │ Coqui TTS │  │   │  │ or OpenAI │  │
    │  └───────────┘  │   │  └───────────┘  │
    └─────────────────┘   └─────────────────┘
```

### Data Flow

**STT (Speech-to-Text)**:
1. Browser captures audio via `getUserMedia()` + `MediaRecorder`
2. Audio chunks streamed to server via WebSocket
3. Server routes to selected STT provider:
   - **Local**: Whisper.cpp or faster-whisper (streaming or chunk-based)
   - **Cloud**: OpenAI Whisper API (streaming or chunk-based)
4. Transcription results streamed back to browser in real-time
5. Browser displays interim + final results

**TTS (Text-to-Speech)**:
1. AI response text received
2. Client requests TTS for text chunks (streaming-friendly)
3. Server routes to selected TTS provider:
   - **Local**: Piper TTS (fast, lightweight) or Coqui TTS
   - **Cloud**: ElevenLabs or OpenAI TTS
4. Audio streamed back as it's generated
5. Browser plays audio via Web Audio API

---

## Implementation Milestones

### Milestone 1: Local STT Foundation ✅ ⬜
**Goal**: Basic speech-to-text working locally

- [ ] Integrate faster-whisper or whisper.cpp for local transcription
- [ ] Create `/api/v1/voice/stt/stream` WebSocket endpoint
- [ ] Implement audio chunking and VAD (Voice Activity Detection)
- [ ] Basic browser audio capture and WebSocket streaming
- [ ] Display transcription in chat input field

**Validation**: Can speak into browser, see text appear in input, reasonable latency (<2s)

---

### Milestone 2: Cloud STT Integration ⬜
**Goal**: Add OpenAI Whisper API as alternative provider

- [ ] Abstract STT provider interface
- [ ] Implement OpenAI Whisper API client with streaming
- [ ] Provider selection UI (Local vs Cloud)
- [ ] API key configuration in settings
- [ ] Graceful fallback if API unavailable

**Validation**: Can switch providers, both work, cloud has lower latency

---

### Milestone 3: Real-time Streaming Polish ⬜
**Goal**: Production-grade latency and UX

- [ ] Optimize audio chunk size and buffering (<500ms end-to-end)
- [ ] Implement sentence-level buffering for natural flow
- [ ] Add confidence scores and visual feedback
- [ ] Handle network interruptions gracefully
- [ ] Support pausing and resuming dictation

**Validation**: Feels responsive, no awkward delays, handles errors gracefully

---

### Milestone 4: TTS (Text-to-Speech) ⬜
**Goal**: AI responses spoken aloud

- [ ] Integrate Piper TTS for local synthesis
- [ ] Create `/api/v1/voice/tts` endpoint with streaming
- [ ] Browser audio playback with queue management
- [ ] Play/pause/mute controls per message
- [ ] Optional: ElevenLabs/OpenAI TTS for cloud option

**Validation**: AI responses are spoken clearly, lip-sync timing feels natural

---

### Milestone 5: Voice Settings and Preferences ⬜
**Goal**: User control over voice experience

- [ ] Voice settings panel in UI
- [ ] Save preferences (provider, voice, auto-read toggle)
- [ ] Microphone permission handling
- [ ] Keyboard shortcuts configuration
- [ ] Mobile browser support testing

**Validation**: Settings persist, permissions handled gracefully, works on mobile

---

### Milestone 6: Testing and Documentation ⬜
**Goal**: Reliable, documented, tested feature

- [ ] Unit tests for STT/TTS providers
- [ ] Integration tests for WebSocket endpoints
- [ ] Browser-based E2E tests for voice flow
- [ ] User documentation: setup, usage, troubleshooting
- [ ] Performance benchmarks (latency, accuracy)

**Validation**: All tests pass, docs are clear, performance meets targets

---

## Technical Specifications

### STT Providers

| Provider | Model | Latency | Quality | Setup Complexity |
|----------|-------|---------|---------|------------------|
| **Local** | faster-whisper (base) | 1-2s | Good | Medium (download model) |
| **Local** | whisper.cpp (tiny) | 500ms | OK | Low (binary + model) |
| **Cloud** | OpenAI Whisper | 200-500ms | Excellent | Low (API key only) |

**Default**: Cloud (OpenAI) for ease of use, Local for privacy-conscious users

### TTS Providers

| Provider | Voices | Latency | Quality | Local? |
|----------|--------|---------|---------|--------|
| **Piper** | 20+ | Fast | Good | ✅ Yes |
| **Coqui** | Many | Medium | Good | ✅ Yes |
| **ElevenLabs** | 1000+ | Medium | Excellent | ❌ Cloud |
| **OpenAI** | 6 | Fast | Good | ❌ Cloud |

**Default**: Piper (local) for TTS to avoid API costs for frequent use

### Audio Specifications

- **Capture**: 16kHz, 16-bit, mono (Whisper optimized)
- **Streaming**: WebSocket with binary audio chunks
- **Chunk size**: 100-300ms of audio (configurable)
- **VAD threshold**: -26dBFS with 300ms padding
- **TTS output**: 24kHz, MP3 or WAV

### Browser Support

- **Chrome/Edge**: Full support (WebRTC + Web Audio)
- **Firefox**: Full support
- **Safari**: Full support (iOS 14.3+)
- **Mobile**: iOS Safari, Chrome Android

---

## Configuration

### Environment Variables

```bash
# STT Configuration
VOICE_STT_PROVIDER=openai        # or "local"
VOICE_LOCAL_MODEL=base           # tiny/base/small for local Whisper
OPENAI_API_KEY=sk-...            # Required if using cloud

# TTS Configuration
VOICE_TTS_PROVIDER=piper         # or "elevenlabs", "openai"
ELEVENLABS_API_KEY=...           # Required if using ElevenLabs
VOICE_DEFAULT_SPEAKER=default    # Voice ID

# Performance
VOICE_STREAMING_CHUNK_MS=200     # Audio chunk size
VOICE_VAD_THRESHOLD=-26          # Voice activity detection dB
VOICE_MAX_RECORDING_SEC=60       # Max recording duration
```

### User Preferences (Stored in USER.md or settings)

```yaml
voice:
  stt_provider: local             # User's preferred STT
  tts_provider: piper             # User's preferred TTS
  auto_read_responses: true       # Auto-play AI responses
  selected_voice: en_US-amy-medium
  keyboard_shortcut: "Ctrl+Shift+V"
```

---

## Error Handling

| Error | User Message | Fallback Behavior |
|-------|--------------|-------------------|
| Mic permission denied | "Please allow microphone access to use voice input" | Show button to open browser settings |
| STT service unavailable | "Voice service unavailable. Please try again or switch to text input." | Auto-switch to text input mode |
| Network interruption | "Connection lost. Reconnecting..." | Buffer locally, retry WebSocket |
| No speech detected | "No speech detected. Try speaking closer to the microphone." | Keep listening, show VAD meter |
| STT confidence low | (show underlined text) | Allow manual editing before send |
| TTS audio failed | "Could not play audio response" | Show text response only |

---

## Security and Privacy

1. **Local mode**: Audio never leaves the machine—ideal for sensitive content
2. **Cloud mode**: Audio sent to OpenAI/ElevenLabs APIs (subject to their privacy policies)
3. **No audio storage**: Transcribed text is saved (as normal chat), but audio chunks are discarded immediately
4. **HTTPS required**: `getUserMedia()` requires secure context
5. **Explicit consent**: Microphone permission requested on first use with clear explanation

---

## Success Criteria

- [ ] **Latency**: End-to-end STT latency <500ms (cloud) or <2s (local)
- [ ] **Accuracy**: Word error rate <10% for clear speech
- [ ] **Reliability**: 99%+ successful transcriptions on good network
- [ ] **UX**: First-time user can start dictating within 30 seconds
- [ ] **Accessibility**: Works with screen readers, keyboard-only navigation
- [ ] **Mobile**: Functional on iOS Safari and Chrome Android
- [ ] **Privacy**: Local mode works completely offline

---

## Dependencies

### Python (Backend)

```toml
[tool.uv]
dependencies = [
    "faster-whisper>=0.10.0",      # Local STT
    "piper-tts>=1.2.0",             # Local TTS
    "websockets>=12.0",             # WebSocket support
    "webrtcvad>=2.0.10",            # Voice activity detection
    "pydub>=0.25.1",                # Audio processing
]
```

### JavaScript (Frontend)

```json
{
  "dependencies": {
    "@ricky0123/vad-web": "^0.2",    // Voice activity detection
    "wavesurfer.js": "^7.7"          // Audio visualization
  }
}
```

---

## Open Questions

1. **Should we support voice commands** (e.g., "Alfred, summarize this") or only dictation?
2. **Multiple languages**: Should we auto-detect or require user selection?
3. **Voice profiles**: Should users train voice recognition for better accuracy?
4. **Offline indicator**: How to clearly show local vs cloud mode status?

---

## Related Work

- PRD #156: Playwright Browser Control (could integrate voice for browser automation)
- PRD #159: Native Application Experience (voice shortcuts fit here)
- ROADMAP: Short-term priority for accessibility and UX

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-26 | Web UI only initially | TUI voice is complex (terminal audio), Telegram has built-in voice |
| 2026-03-26 | Dual local/cloud support | Privacy-conscious users want local; casual users want convenience |
| 2026-03-26 | WebSocket streaming | Lower latency than HTTP polling, standard for real-time audio |
| 2026-03-26 | Piper for local TTS | Fast, lightweight, good quality, no GPU needed |
