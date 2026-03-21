const DEFAULT_AUDIO_ASSETS = Object.freeze({
  music: '/static/audio/kidcore-loop.mp3',
  click: '/static/audio/click.mp3',
  send: '/static/audio/send.mp3',
  complete: '/static/audio/success.mp3',
  error: '/static/audio/error.mp3',
});

const EFFECT_VOLUME = Object.freeze({
  click: 0.36,
  send: 0.48,
  complete: 0.58,
  error: 0.58,
});

function createAudioElement(source, { loop = false, volume = 1 } = {}) {
  const audio = new Audio(source);
  audio.loop = loop;
  audio.preload = 'auto';
  audio.volume = volume;
  return audio;
}

function cleanupAudio(audio) {
  try {
    audio.pause();
  } catch {
    // Ignore teardown errors; audio is best-effort only.
  }

  audio.currentTime = 0;
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function randomBetween(min, max) {
  return min + Math.random() * (max - min);
}

export class KidcoreAudioManager {
  constructor(assets = {}) {
    this._assets = { ...DEFAULT_AUDIO_ASSETS, ...assets };
    this._music = null;
    this._muted = false;
    this._musicRequested = false;
    this._musicPlaying = false;
    this._lastError = null;
    this._activeEffects = new Set();
    this._audioContext = null;
    this._masterGain = null;
    this._visibilityHandler = null;

    if (typeof document !== 'undefined') {
      this._visibilityHandler = () => {
        if (document.hidden) {
          this.stopMusic();
        }
      };
      document.addEventListener('visibilitychange', this._visibilityHandler);
    }
  }

  get isMuted() {
    return this._muted;
  }

  get isMusicPlaying() {
    return this._musicPlaying;
  }

  get lastError() {
    return this._lastError;
  }

  _rememberError(error) {
    this._lastError = error instanceof Error ? error : new Error(String(error));
    console.warn('Kidcore audio playback failed:', this._lastError);
  }

  _ensureAudioContext() {
    if (typeof window === 'undefined') {
      return null;
    }

    const AudioCtor = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtor) {
      return null;
    }

    if (!this._audioContext) {
      this._audioContext = new AudioCtor();
      this._masterGain = this._audioContext.createGain();
      this._masterGain.gain.value = 0.88;
      this._masterGain.connect(this._audioContext.destination);
    }

    if (this._audioContext.state === 'suspended') {
      void this._audioContext.resume().catch((error) => {
        this._rememberError(error);
      });
    }

    return this._audioContext;
  }

  _routeSynthToMaster(node) {
    if (this._masterGain) {
      node.connect(this._masterGain);
    }
  }

  _playTone({
    startFrequency,
    endFrequency = null,
    duration = 0.08,
    waveform = 'triangle',
    gain = 0.04,
    delay = 0,
    detune = 0,
    filterFrequency = null,
    filterQ = 0.9,
  }) {
    const context = this._ensureAudioContext();
    if (!context || this._muted) {
      return false;
    }

    const now = context.currentTime + 0.01 + delay;
    const end = now + duration;
    const oscillator = context.createOscillator();
    const filter = context.createBiquadFilter();
    const gainNode = context.createGain();

    oscillator.type = waveform;
    oscillator.frequency.setValueAtTime(startFrequency, now);
    oscillator.detune.setValueAtTime(detune, now);
    if (endFrequency !== null && endFrequency !== startFrequency) {
      oscillator.frequency.exponentialRampToValueAtTime(clamp(endFrequency, 1, 20000), end);
    }

    filter.type = 'lowpass';
    filter.frequency.value = filterFrequency ?? clamp(startFrequency * 2.8, 1200, 12000);
    filter.Q.value = filterQ;

    gainNode.gain.setValueAtTime(0.0001, now);
    gainNode.gain.exponentialRampToValueAtTime(gain, now + Math.min(0.015, duration * 0.3));
    gainNode.gain.exponentialRampToValueAtTime(0.0001, end + 0.02);

    oscillator.connect(filter);
    filter.connect(gainNode);
    this._routeSynthToMaster(gainNode);

    oscillator.start(now);
    oscillator.stop(end + 0.05);
    return true;
  }

  _playNoiseBurst({
    duration = 0.05,
    gain = 0.018,
    delay = 0,
    filterFrequency = 2400,
    filterQ = 9,
  }) {
    const context = this._ensureAudioContext();
    if (!context || this._muted) {
      return false;
    }

    const start = context.currentTime + 0.01 + delay;
    const length = Math.max(1, Math.floor(context.sampleRate * duration));
    const buffer = context.createBuffer(1, length, context.sampleRate);
    const channel = buffer.getChannelData(0);

    for (let index = 0; index < channel.length; index += 1) {
      const falloff = 1 - index / channel.length;
      channel[index] = (Math.random() * 2 - 1) * falloff;
    }

    const source = context.createBufferSource();
    const filter = context.createBiquadFilter();
    const gainNode = context.createGain();

    source.buffer = buffer;
    filter.type = 'bandpass';
    filter.frequency.value = filterFrequency;
    filter.Q.value = filterQ;

    gainNode.gain.setValueAtTime(0.0001, start);
    gainNode.gain.exponentialRampToValueAtTime(gain, start + 0.01);
    gainNode.gain.exponentialRampToValueAtTime(0.0001, start + duration);

    source.connect(filter);
    filter.connect(gainNode);
    this._routeSynthToMaster(gainNode);

    source.start(start);
    source.stop(start + duration + 0.02);
    return true;
  }

  _trackEffect(audio) {
    this._activeEffects.add(audio);
    const cleanup = () => {
      this._activeEffects.delete(audio);
      audio.removeEventListener('ended', cleanup);
      audio.removeEventListener('error', cleanup);
      cleanupAudio(audio);
    };

    audio.addEventListener('ended', cleanup);
    audio.addEventListener('error', cleanup);
  }

  _playAudio(audio) {
    try {
      const result = audio.play();
      if (result && typeof result.catch === 'function') {
        result.catch((error) => {
          this._rememberError(error);
        });
      }
      return true;
    } catch (error) {
      this._rememberError(error);
      return false;
    }
  }

  _playSynthClick() {
    const playedPrimary = this._playTone({
      startFrequency: 920,
      endFrequency: 760,
      duration: 0.05,
      waveform: 'triangle',
      gain: 0.045,
      filterFrequency: 2400,
    });
    const playedSparkle = this._playTone({
      startFrequency: 1480,
      endFrequency: 1260,
      duration: 0.028,
      waveform: 'sine',
      gain: 0.016,
      delay: 0.012,
      filterFrequency: 5000,
      filterQ: 0.7,
    });
    return playedPrimary || playedSparkle;
  }

  _playSynthSend() {
    const playedPrimary = this._playTone({
      startFrequency: 640,
      endFrequency: 920,
      duration: 0.09,
      waveform: 'sine',
      gain: 0.05,
      filterFrequency: 1800,
    });
    const playedAccent = this._playTone({
      startFrequency: 1180,
      endFrequency: 860,
      duration: 0.055,
      waveform: 'triangle',
      gain: 0.022,
      delay: 0.02,
      filterFrequency: 4300,
    });
    return playedPrimary || playedAccent;
  }

  _playSynthChunk() {
    const glimmer = this._playTone({
      startFrequency: 1040,
      endFrequency: 780,
      duration: 0.048,
      waveform: 'triangle',
      gain: 0.038,
      filterFrequency: 3200,
    });
    const pop = this._playTone({
      startFrequency: 1520,
      endFrequency: 1240,
      duration: 0.024,
      waveform: 'sine',
      gain: 0.015,
      delay: 0.012,
      filterFrequency: 5600,
    });
    return glimmer || pop;
  }

  _playSynthComplete() {
    const noteOne = this._playTone({
      startFrequency: 720,
      endFrequency: 1040,
      duration: 0.07,
      waveform: 'triangle',
      gain: 0.038,
      filterFrequency: 3600,
    });
    const noteTwo = this._playTone({
      startFrequency: 960,
      endFrequency: 1280,
      duration: 0.07,
      waveform: 'sine',
      gain: 0.03,
      delay: 0.05,
      filterFrequency: 4800,
    });
    const sparkle = this._playNoiseBurst({
      duration: 0.06,
      gain: 0.014,
      delay: 0.035,
    });
    return noteOne || noteTwo || sparkle;
  }

  _playSynthError() {
    const buzz = this._playTone({
      startFrequency: 260,
      endFrequency: 160,
      duration: 0.14,
      waveform: 'sawtooth',
      gain: 0.03,
      filterFrequency: 900,
      filterQ: 1.8,
    });
    const wobble = this._playTone({
      startFrequency: 180,
      endFrequency: 120,
      duration: 0.09,
      waveform: 'square',
      gain: 0.02,
      delay: 0.018,
      filterFrequency: 700,
      filterQ: 2.2,
    });
    return buzz || wobble;
  }

  startMusic() {
    this._musicRequested = true;

    if (this._muted || typeof Audio === 'undefined') {
      return false;
    }

    const music = this._ensureMusic();
    music.loop = true;
    music.muted = false;
    music.volume = 0.32;
    this._musicPlaying = true;
    return this._playAudio(music);
  }

  _ensureMusic() {
    if (this._music) {
      return this._music;
    }

    this._music = createAudioElement(this._assets.music, { loop: true, volume: 0.32 });
    this._music.addEventListener('ended', () => {
      this._musicPlaying = false;
    });
    this._music.addEventListener('pause', () => {
      this._musicPlaying = false;
    });
    return this._music;
  }

  stopMusic({ preserveIntent = false } = {}) {
    if (!preserveIntent) {
      this._musicRequested = false;
    }

    this._musicPlaying = false;

    if (!this._music) {
      return false;
    }

    cleanupAudio(this._music);
    return true;
  }

  setMuted(isMuted) {
    const nextMuted = Boolean(isMuted);

    if (this._muted === nextMuted) {
      return true;
    }

    this._muted = nextMuted;

    if (this._muted) {
      this.stopMusic({ preserveIntent: true });
      return true;
    }

    if (this._musicRequested) {
      return this.startMusic();
    }

    return true;
  }

  mute() {
    return this.setMuted(true);
  }

  unmute() {
    return this.setMuted(false);
  }

  toggleMute() {
    return this.setMuted(!this._muted);
  }

  playEffect(effectName, options = {}) {
    if (this._muted || typeof Audio === 'undefined') {
      return false;
    }

    const source = this._assets[effectName];
    if (!source) {
      this._rememberError(new Error(`Unknown kidcore audio effect: ${effectName}`));
      return false;
    }

    const audio = createAudioElement(source, {
      loop: false,
      volume: options.volume ?? EFFECT_VOLUME[effectName] ?? 0.5,
    });

    if (options.playbackRate) {
      audio.playbackRate = options.playbackRate;
    }

    this._trackEffect(audio);
    return this._playAudio(audio);
  }

  playClick() {
    return this._playSynthClick() || this.playEffect('click', { volume: EFFECT_VOLUME.click });
  }

  playSend() {
    return this._playSynthSend() || this.playEffect('send', { volume: EFFECT_VOLUME.send });
  }

  playChunk() {
    return this._playSynthChunk() || this.playEffect('click', { volume: 0.26, playbackRate: 1.08 });
  }

  playMessageComplete() {
    const synthPlayed = this._playSynthComplete();
    const filePlayed = this.playEffect('complete', { volume: EFFECT_VOLUME.complete, playbackRate: 1.02 });
    return synthPlayed || filePlayed;
  }

  playSuccess() {
    return this.playMessageComplete();
  }

  playError() {
    const synthPlayed = this._playSynthError();
    const filePlayed = this.playEffect('error', { volume: EFFECT_VOLUME.error, playbackRate: 0.96 });
    return synthPlayed || filePlayed;
  }

  stopAll() {
    this.stopMusic();
    this._activeEffects.forEach((audio) => cleanupAudio(audio));
    this._activeEffects.clear();
  }

  destroy() {
    this.stopAll();

    if (this._visibilityHandler && typeof document !== 'undefined') {
      document.removeEventListener('visibilitychange', this._visibilityHandler);
    }

    this._visibilityHandler = null;
    this._music = null;
  }
}

export const audioManager = new KidcoreAudioManager();

if (typeof window !== 'undefined') {
  window.kidcoreAudioManager = audioManager;
}
