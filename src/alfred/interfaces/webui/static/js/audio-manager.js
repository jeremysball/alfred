const DEFAULT_AUDIO_ASSETS = Object.freeze({
  music: '/static/audio/kidcore-loop.mp3',
  click: '/static/audio/click.mp3',
  send: '/static/audio/send.mp3',
  success: '/static/audio/success.mp3',
  error: '/static/audio/error.mp3',
});

const EFFECT_VOLUME = Object.freeze({
  click: 0.42,
  send: 0.55,
  success: 0.68,
  error: 0.68,
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

export class KidcoreAudioManager {
  constructor(assets = {}) {
    this._assets = { ...DEFAULT_AUDIO_ASSETS, ...assets };
    this._music = null;
    this._muted = false;
    this._musicRequested = false;
    this._musicPlaying = false;
    this._lastError = null;
    this._activeEffects = new Set();
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
    return this.playEffect('click');
  }

  playSend() {
    return this.playEffect('send');
  }

  playSuccess() {
    return this.playEffect('success');
  }

  playError() {
    return this.playEffect('error');
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
