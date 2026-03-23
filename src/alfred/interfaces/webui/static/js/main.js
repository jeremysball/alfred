// Alfred Web UI - Main JavaScript
import { applyThemeContrast } from './utils/contrast.js';

/**
 * Initialize the Alfred Web UI
 */
function initAlfredUI() {
  console.log('Initializing Alfred Web UI...');

  // Apply initial contrast
  applyThemeContrast();

  // DOM Elements
  const messageList = document.getElementById('message-list');
  const messageInput = document.getElementById('message-input');
  const sendButton = document.getElementById('send-button');
  const connectionPill = document.getElementById('connection-pill');
  const connectionStatusAnchor = document.getElementById('connection-status-anchor');
  const connectionStatusTooltip = document.getElementById('connection-status-tooltip');
  const chatContainer = document.getElementById('chat-container');
  const queueBadge = document.getElementById('queue-badge');

  const completionMenu = document.getElementById('completion-menu');
  const kidcoreAudioControls = document.querySelector('.kidcore-audio-controls');
  const kidcoreAudioManager = window.kidcoreAudioManager ?? null;
  const kidcoreMusicPlayButton = document.getElementById('kidcore-music-play');
  const kidcoreMusicMuteButton = document.getElementById('kidcore-music-mute');
  const kidcoreSfxToggleButton = document.getElementById('kidcore-sfx-toggle');
  const kidcoreMusicStatus = document.getElementById('kidcore-music-status');
  const kidcoreSfxStatus = document.getElementById('kidcore-sfx-status');

  const KIDCORE_THEME_ID = 'kidcore-playground';
  let pendingKidcoreStreamingFx = null;

  function isKidcoreThemeActive() {
    return document.documentElement.getAttribute('data-theme') === KIDCORE_THEME_ID;
  }

  function playKidcoreClick() {
    if (!isKidcoreThemeActive() || !kidcoreAudioManager) {
      return;
    }
    kidcoreAudioManager.playClick?.();
  }

  function playKidcoreSend() {
    if (!isKidcoreThemeActive() || !kidcoreAudioManager) {
      return;
    }
    kidcoreAudioManager.playSend?.();
  }

  function playKidcoreChunk() {
    if (!isKidcoreThemeActive() || !kidcoreAudioManager) {
      return;
    }
    kidcoreAudioManager.playChunk?.();
  }

  function playKidcoreSuccess() {
    playKidcoreMessageComplete();
  }

  function playKidcoreMessageComplete() {
    if (!isKidcoreThemeActive() || !kidcoreAudioManager) {
      return;
    }
    kidcoreAudioManager.playMessageComplete?.();
  }

  function playKidcoreError() {
    if (!isKidcoreThemeActive() || !kidcoreAudioManager) {
      return;
    }
    kidcoreAudioManager.playError?.();
  }

  function syncKidcoreAudioControls() {
    if (!kidcoreAudioControls || !kidcoreAudioManager) {
      return;
    }

    const isKidcore = isKidcoreThemeActive();
    const isMusicMuted = isKidcore && kidcoreAudioManager.isMusicMuted;
    const isMusicPlaying = isKidcore && kidcoreAudioManager.isMusicPlaying;
    const isSfxMuted = isKidcore && kidcoreAudioManager.isSfxMuted;

    kidcoreAudioControls.dataset.audioState = !isKidcore ? 'disabled' : isMusicMuted ? 'muted' : isMusicPlaying ? 'playing' : 'idle';
    kidcoreAudioControls.dataset.musicState = !isKidcore ? 'disabled' : isMusicMuted ? 'muted' : isMusicPlaying ? 'playing' : 'idle';
    kidcoreAudioControls.dataset.sfxState = !isKidcore ? 'disabled' : isSfxMuted ? 'muted' : 'on';

    if (kidcoreMusicStatus) {
      kidcoreMusicStatus.textContent = !isKidcore ? 'Hidden' : isMusicMuted ? 'Muted' : isMusicPlaying ? 'Playing' : 'Ready';
    }

    if (kidcoreSfxStatus) {
      kidcoreSfxStatus.textContent = !isKidcore ? 'Hidden' : isSfxMuted ? 'Muted' : 'On';
    }

    kidcoreMusicPlayButton?.setAttribute('aria-pressed', String(isKidcore && isMusicPlaying));
    kidcoreMusicMuteButton?.setAttribute('aria-pressed', String(isKidcore && isMusicMuted));
    kidcoreSfxToggleButton?.setAttribute('aria-pressed', String(isKidcore && isSfxMuted));
    if (kidcoreSfxToggleButton) {
      kidcoreSfxToggleButton.textContent = !isKidcore ? '🔊 SFX' : isSfxMuted ? '🔇 SFX Off' : '🔊 SFX On';
    }
  }

  function resumeKidcoreMusic() {
    if (!isKidcoreThemeActive() || !kidcoreAudioManager) {
      return;
    }

    kidcoreAudioManager.unmuteMusic?.();
    if (!kidcoreAudioManager.isMusicPlaying) {
      kidcoreAudioManager.startMusic?.();
    }
    syncKidcoreAudioControls();
  }

  function applyGlueShimmerEffect(messageEl) {
    if (pendingKidcoreStreamingFx !== 'glue-shimmer' || !messageEl) {
      return;
    }

    messageEl.classList.add('glue-shimmer');
    messageEl.setAttribute('data-stream-fx', 'glue-shimmer');
  }

  function pulseGlueShimmer(messageEl) {
    if (pendingKidcoreStreamingFx !== 'glue-shimmer' || !messageEl) {
      return;
    }

    const bubble = messageEl.querySelector('.message-bubble');
    if (!bubble) {
      return;
    }

    bubble.classList.remove('glue-shimmer-pulse');
    void bubble.offsetWidth;
    bubble.classList.add('glue-shimmer-pulse');
  }

  function clearGlueShimmerEffect(messageEl) {
    if (messageEl) {
      messageEl.classList.remove('glue-shimmer');
      messageEl.removeAttribute('data-stream-fx');
      const bubble = messageEl.querySelector('.message-bubble');
      bubble?.classList.remove('glue-shimmer-pulse');
    }
    pendingKidcoreStreamingFx = null;
  }

  const themeObserver = new MutationObserver(() => {
    if (!isKidcoreThemeActive()) {
      kidcoreAudioManager?.stopAll?.();
      pendingKidcoreStreamingFx = null;
    }
    syncKidcoreAudioControls();
  });
  themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });

  kidcoreMusicPlayButton?.addEventListener('click', () => {
    resumeKidcoreMusic();
    playKidcoreClick();
  });

  kidcoreMusicMuteButton?.addEventListener('click', () => {
    playKidcoreClick();
    kidcoreAudioManager?.muteMusic?.();
    syncKidcoreAudioControls();
  });

  kidcoreSfxToggleButton?.addEventListener('click', () => {
    const wasMuted = Boolean(kidcoreAudioManager?.isSfxMuted);
    kidcoreAudioManager?.toggleSfxMute?.();
    if (wasMuted) {
      playKidcoreClick();
    }
    syncKidcoreAudioControls();
  });

  syncKidcoreAudioControls();

  function getSessionMessageId(msg, fallbackIndex = '') {
    return String(msg?.id ?? msg?.messageId ?? msg?.idx ?? fallbackIndex);
  }

  function applySessionMessageState(messageEl, msg, { preserveExistingAssistantContent = false } = {}) {
    if (!messageEl || !msg) {
      return;
    }

    const role = msg.role || 'user';
    const messageId = getSessionMessageId(msg);
    const loadedContent = msg.content || '';
    const loadedTimestamp = msg.timestamp || msg.createdAt || new Date().toISOString();
    const existingContent = typeof messageEl.getContent === 'function'
      ? messageEl.getContent()
      : (messageEl.getAttribute('content') || '');
    const contentToSet = preserveExistingAssistantContent && role === 'assistant' && existingContent.length > loadedContent.length
      ? existingContent
      : loadedContent;
    const existingReasoning = typeof messageEl.getReasoning === 'function'
      ? messageEl.getReasoning()
      : (messageEl.getAttribute('reasoning') || '');
    const loadedReasoning = msg.reasoningContent || '';

    messageEl.setAttribute('data-session-message', 'true');
    messageEl.setAttribute('role', role);
    messageEl.setAttribute('content', contentToSet);
    messageEl.setAttribute('timestamp', loadedTimestamp);

    if (messageId) {
      messageEl.setAttribute('message-id', messageId);
    } else {
      messageEl.removeAttribute('message-id');
    }

    if (role === 'assistant' && msg.streaming) {
      messageEl.classList.add('streaming');
    } else {
      messageEl.classList.remove('streaming');
    }

    if (loadedReasoning || !preserveExistingAssistantContent) {
      if (!preserveExistingAssistantContent || loadedReasoning.length >= existingReasoning.length) {
        messageEl.setReasoning(loadedReasoning);
      }
    }

    if (Array.isArray(msg.toolCalls) && (msg.toolCalls.length > 0 || !preserveExistingAssistantContent)) {
      messageEl.setToolCalls(msg.toolCalls);
    }
  }

  function reconcileSessionLoaded(payload) {
    const messages = Array.isArray(payload?.messages) ? payload.messages : [];
    const incomingSessionId = payload?.sessionId || null;
    const incomingMessageIds = new Set(messages.map((msg, index) => getSessionMessageId(msg, index)));
    const currentAssistantId = currentAssistantMessage?.getAttribute('message-id') || null;
    const preserveOrphanAssistant = Boolean(
      currentAssistantMessage &&
      currentAssistantMessage.classList.contains('streaming') &&
      currentAssistantId &&
      (!activeSessionId || activeSessionId === incomingSessionId)
    );

    const existingSessionMessages = Array.from(messageList.querySelectorAll('chat-message[data-session-message="true"]'));
    const existingById = new Map();

    // Remove ephemeral UI-only messages before we rebuild the loaded session state.
    Array.from(messageList.children).forEach((child) => {
      if (child.matches?.('chat-message[data-session-message="true"]')) {
        return;
      }
      child.remove();
    });

    messageHistory.length = 0;
    historyIndex = -1;
    activeToolCalls.clear();

    existingSessionMessages.forEach((messageEl) => {
      const messageId = messageEl.getAttribute('message-id');
      if (messageId) {
        existingById.set(messageId, messageEl);
      }
    });

    existingSessionMessages.forEach((messageEl) => {
      const messageId = messageEl.getAttribute('message-id');
      if (!messageId) {
        if (!(messageEl === currentAssistantMessage && preserveOrphanAssistant)) {
          messageEl.remove();
        }
        return;
      }

      if (!incomingMessageIds.has(messageId) && (!preserveOrphanAssistant || messageId !== currentAssistantId)) {
        messageEl.remove();
      }
    });

    const fragment = document.createDocumentFragment();
    let nextCurrentAssistantMessage = null;

    messages.forEach((msg, index) => {
      const messageId = getSessionMessageId(msg, index);
      let messageEl = existingById.get(messageId) || null;

      if (messageEl) {
        applySessionMessageState(messageEl, msg, {
          preserveExistingAssistantContent: messageEl === currentAssistantMessage,
        });
      } else {
        messageEl = document.createElement('chat-message');
        applySessionMessageState(messageEl, msg);
      }

      fragment.appendChild(messageEl);

      if (msg.role === 'user') {
        messageHistory.push(msg.content || '');
      }

      if (msg.role === 'assistant' && msg.streaming) {
        nextCurrentAssistantMessage = messageEl;
      }
    });

    if (preserveOrphanAssistant && currentAssistantMessage && currentAssistantId && !incomingMessageIds.has(currentAssistantId)) {
      applySessionMessageState(currentAssistantMessage, {
        role: 'assistant',
        content: typeof currentAssistantMessage.getContent === 'function'
          ? currentAssistantMessage.getContent()
          : (currentAssistantMessage.getAttribute('content') || ''),
        id: currentAssistantId,
        timestamp: currentAssistantMessage.getAttribute('timestamp') || new Date().toISOString(),
        reasoningContent: typeof currentAssistantMessage.getReasoning === 'function'
          ? currentAssistantMessage.getReasoning()
          : '',
        streaming: true,
      }, {
        preserveExistingAssistantContent: true,
      });
      fragment.appendChild(currentAssistantMessage);
      nextCurrentAssistantMessage = currentAssistantMessage;
    }

    messageList.appendChild(fragment);
    currentAssistantMessage = nextCurrentAssistantMessage;
    activeSessionId = incomingSessionId;
    historyIndex = messageHistory.length;
  }

  // WebSocket Client
  const wsClient = new AlfredWebSocketClient();
  let currentAssistantMessage = null;
  let activeSessionId = null;
  const activeToolCalls = new Map();
  let allToolsExpanded = false;

  // Message Queue
  const messageQueue = [];

  // Message History
  const messageHistory = [];
  let historyIndex = -1;

  // Available Commands
  const commands = [
    { value: '/new', description: 'Start new session' },
    { value: '/resume', description: 'Resume a session' },
    { value: '/sessions', description: 'List recent sessions' },
    { value: '/session', description: 'Show current session info' },
    { value: '/context', description: 'Show system context' },
    { value: '/help', description: 'Show available commands' }
  ];

  // Connection Status Handler
  const connectionStatusState = {
    daemonStatus: 'unknown',
    daemonPid: null,
    webUiStatus: 'ready',
    webUiVersion: 'unknown',
  };

  const connectionStatusVisibility = {
    hovered: false,
    focused: false,
    pinned: false,
  };

  let connectionStatusRefreshTimer = null;

  function escapeConnectionStatusText(value) {
    const div = document.createElement('div');
    div.textContent = String(value ?? '');
    return div.innerHTML;
  }

  function formatConnectionStatusAge(timestamp) {
    if (!timestamp) {
      return 'n/a';
    }

    const elapsedMs = Math.max(Date.now() - timestamp, 0);
    if (elapsedMs < 1000) {
      return `${elapsedMs}ms ago`;
    }

    const elapsedSeconds = Math.round(elapsedMs / 1000);
    if (elapsedSeconds < 60) {
      return `${elapsedSeconds}s ago`;
    }

    const elapsedMinutes = Math.round(elapsedSeconds / 60);
    if (elapsedMinutes < 60) {
      return `${elapsedMinutes}m ago`;
    }

    const elapsedHours = Math.round(elapsedMinutes / 60);
    return `${elapsedHours}h ago`;
  }

  function getConnectionSnapshot() {
    if (typeof wsClient.getConnectionSnapshot === 'function') {
      return wsClient.getConnectionSnapshot();
    }

    const readyState = wsClient.ws?.readyState;
    return {
      url: wsClient.url,
      isConnected: wsClient.isConnected,
      connectionState: wsClient.isConnected
        ? 'connected'
        : readyState === WebSocket.CONNECTING
          ? 'connecting'
          : wsClient.reconnectAttempts > 0
            ? 'reconnecting'
            : 'disconnected',
      readyState,
      reconnectAttempts: wsClient.reconnectAttempts,
      pingIntervalActive: Boolean(wsClient.pingInterval),
      lastPingAt: wsClient.lastPingAt ?? null,
      lastPongAt: wsClient.lastPongAt ?? null,
      lastPingLatencyMs: wsClient.lastPingLatencyMs ?? null,
      lastCloseAt: wsClient.lastCloseAt ?? null,
      lastCloseCode: wsClient.lastCloseCode ?? null,
      lastCloseReason: wsClient.lastCloseReason ?? '',
      lastCloseWasClean: wsClient.lastCloseWasClean ?? null,
      debugEnabled: Boolean(wsClient.debugEnabled),
      debugSummary: wsClient.debugStats?.summary?.() ?? null,
    };
  }

  function getWebSocketStateLabel(snapshot) {
    if (snapshot?.connectionState) {
      return snapshot.connectionState;
    }
    if (snapshot?.isConnected) {
      return 'connected';
    }
    if (snapshot?.readyState === WebSocket.CONNECTING) {
      return 'connecting';
    }
    if (snapshot?.readyState === WebSocket.CLOSING) {
      return 'closing';
    }
    if ((snapshot?.reconnectAttempts || 0) > 0) {
      return 'reconnecting';
    }
    return 'disconnected';
  }

  function getLastCloseLabel(snapshot, debugSummary) {
    const closeCode = snapshot?.lastCloseCode ?? debugSummary?.closeCode;
    const closeReason = snapshot?.lastCloseReason ?? debugSummary?.closeReason;
    const wasClean = snapshot?.lastCloseWasClean ?? debugSummary?.wasClean;

    if (closeCode === null || closeCode === undefined) {
      return 'none';
    }

    const parts = [`code ${closeCode}`];
    if (closeReason) {
      parts.push(closeReason);
    }
    if (wasClean !== null && wasClean !== undefined) {
      parts.push(wasClean ? 'clean' : 'unclean');
    }
    return parts.join(' · ');
  }

  function getKeepaliveLabel(snapshot) {
    if (!snapshot?.pingIntervalActive) {
      return 'idle';
    }

    const pongAge = snapshot.lastPongAt ? formatConnectionStatusAge(snapshot.lastPongAt) : 'no pong yet';
    return `active · last pong ${pongAge}`;
  }

  function isConnectionStatusOpen() {
    return connectionStatusVisibility.hovered || connectionStatusVisibility.focused || connectionStatusVisibility.pinned;
  }

  function startConnectionStatusRefreshTimer() {
    if (connectionStatusRefreshTimer !== null) {
      return;
    }

    connectionStatusRefreshTimer = window.setInterval(() => {
      if (isConnectionStatusOpen()) {
        renderConnectionStatusTooltip();
      } else {
        stopConnectionStatusRefreshTimer();
      }
    }, 1000);
  }

  function stopConnectionStatusRefreshTimer() {
    if (connectionStatusRefreshTimer === null) {
      return;
    }

    window.clearInterval(connectionStatusRefreshTimer);
    connectionStatusRefreshTimer = null;
  }

  function syncConnectionStatusPopoverVisibility() {
    if (!connectionStatusAnchor || !connectionStatusTooltip || !connectionPill) {
      return;
    }

    const isOpen = isConnectionStatusOpen();
    connectionStatusAnchor.dataset.open = String(isOpen);
    connectionStatusAnchor.dataset.pinned = String(connectionStatusVisibility.pinned);
    connectionStatusAnchor.setAttribute('aria-expanded', String(isOpen));
    connectionStatusTooltip.setAttribute('aria-hidden', String(!isOpen));
    connectionPill.setAttribute('aria-expanded', String(isOpen));

    if (isOpen) {
      startConnectionStatusRefreshTimer();
    } else {
      stopConnectionStatusRefreshTimer();
    }

    renderConnectionStatusTooltip();
  }

  function renderConnectionStatusTooltip() {
    if (!connectionStatusTooltip) {
      return;
    }

    const snapshot = getConnectionSnapshot();
    const debugSummary = snapshot.debugSummary || null;
    const websocketState = getWebSocketStateLabel(snapshot);
    const websocketEndpoint = snapshot.url || 'n/a';
    const reconnectAttempts = snapshot.reconnectAttempts ?? 0;
    const lastClose = getLastCloseLabel(snapshot, debugSummary);
    const keepalive = getKeepaliveLabel(snapshot);
    const debugState = snapshot.debugEnabled ? 'enabled' : 'off';
    const lastPing = snapshot.lastPingAt ? formatConnectionStatusAge(snapshot.lastPingAt) : 'n/a';
    const lastPong = snapshot.lastPongAt ? formatConnectionStatusAge(snapshot.lastPongAt) : 'n/a';
    const latency = snapshot.lastPingLatencyMs !== null && snapshot.lastPingLatencyMs !== undefined
      ? `${snapshot.lastPingLatencyMs}ms`
      : 'n/a';

    connectionStatusTooltip.innerHTML = `
      <div class="connection-status-tooltip-title">Connection details</div>
      <div class="connection-status-tooltip-section">
        <div class="connection-status-tooltip-section-title">WebSocket: ${escapeConnectionStatusText(websocketState)}</div>
        <div class="connection-status-tooltip-row">
          <span class="connection-status-tooltip-label">Endpoint</span>
          <span class="connection-status-tooltip-value">${escapeConnectionStatusText(websocketEndpoint)}</span>
        </div>
        <div class="connection-status-tooltip-row">
          <span class="connection-status-tooltip-label">Reconnect attempts</span>
          <span class="connection-status-tooltip-value">${escapeConnectionStatusText(reconnectAttempts)}</span>
        </div>
        <div class="connection-status-tooltip-note">Reconnect attempts: ${escapeConnectionStatusText(reconnectAttempts)}</div>
        <div class="connection-status-tooltip-row">
          <span class="connection-status-tooltip-label">Last close</span>
          <span class="connection-status-tooltip-value">${escapeConnectionStatusText(lastClose)}</span>
        </div>
        <div class="connection-status-tooltip-note">Last close: ${escapeConnectionStatusText(lastClose)}</div>
      </div>
      <div class="connection-status-tooltip-section">
        <div class="connection-status-tooltip-section-title">Daemon: ${escapeConnectionStatusText(connectionStatusState.daemonStatus)}</div>
        <div class="connection-status-tooltip-row">
          <span class="connection-status-tooltip-label">PID</span>
          <span class="connection-status-tooltip-value">${escapeConnectionStatusText(connectionStatusState.daemonPid ?? 'n/a')}</span>
        </div>
        <div class="connection-status-tooltip-note">PID: ${escapeConnectionStatusText(connectionStatusState.daemonPid ?? 'n/a')}</div>
      </div>
      <div class="connection-status-tooltip-section">
        <div class="connection-status-tooltip-section-title">Web UI: ${escapeConnectionStatusText(connectionStatusState.webUiStatus)}</div>
        <div class="connection-status-tooltip-row">
          <span class="connection-status-tooltip-label">Version</span>
          <span class="connection-status-tooltip-value">${escapeConnectionStatusText(connectionStatusState.webUiVersion)}</span>
        </div>
      </div>
      <div class="connection-status-tooltip-section">
        <div class="connection-status-tooltip-section-title">Keepalive: ${escapeConnectionStatusText(keepalive)}</div>
        <div class="connection-status-tooltip-row">
          <span class="connection-status-tooltip-label">Last ping</span>
          <span class="connection-status-tooltip-value">${escapeConnectionStatusText(lastPing)}</span>
        </div>
        <div class="connection-status-tooltip-row">
          <span class="connection-status-tooltip-label">Last pong</span>
          <span class="connection-status-tooltip-value">${escapeConnectionStatusText(lastPong)}</span>
        </div>
        <div class="connection-status-tooltip-row">
          <span class="connection-status-tooltip-label">Latency</span>
          <span class="connection-status-tooltip-value">${escapeConnectionStatusText(latency)}</span>
        </div>
      </div>
      <div class="connection-status-tooltip-section">
        <div class="connection-status-tooltip-section-title">Debug: ${escapeConnectionStatusText(debugState)}</div>
        <div class="connection-status-tooltip-row">
          <span class="connection-status-tooltip-label">Last incoming</span>
          <span class="connection-status-tooltip-value">${escapeConnectionStatusText(debugSummary?.lastIncomingType || 'n/a')}</span>
        </div>
        <div class="connection-status-tooltip-row">
          <span class="connection-status-tooltip-label">Last outgoing</span>
          <span class="connection-status-tooltip-value">${escapeConnectionStatusText(debugSummary?.lastOutgoingType || 'n/a')}</span>
        </div>
      </div>
    `;
  }

  function applyDaemonStatusPayload(payload) {
    if (!payload) {
      return;
    }

    if (payload.daemonStatus !== undefined) {
      connectionStatusState.daemonStatus = String(payload.daemonStatus || 'unknown');
    }
    if (payload.daemonPid !== undefined) {
      connectionStatusState.daemonPid = payload.daemonPid;
    }
    if (payload.status !== undefined) {
      connectionStatusState.webUiStatus = payload.status === 'ok'
        ? 'ready'
        : String(payload.status || 'unknown');
    }
    if (payload.version !== undefined) {
      connectionStatusState.webUiVersion = String(payload.version || 'unknown');
    }

    renderConnectionStatusTooltip();
  }

  async function hydrateConnectionStatusFromHealth() {
    if (typeof fetch !== 'function') {
      return;
    }

    try {
      const response = await fetch('/health', { cache: 'no-store' });
      if (!response.ok) {
        return;
      }

      const payload = await response.json();
      applyDaemonStatusPayload(payload);
    } catch (error) {
      console.debug('Unable to hydrate connection status from /health:', error);
    }
  }

  function updateConnectionStatus(status) {
    connectionPill.className = `connection-pill ${status}`;
    renderConnectionStatusTooltip();
  }

  connectionStatusAnchor?.addEventListener('pointerenter', () => {
    connectionStatusVisibility.hovered = true;
    syncConnectionStatusPopoverVisibility();
  });

  connectionStatusAnchor?.addEventListener('pointerleave', () => {
    connectionStatusVisibility.hovered = false;
    if (!connectionStatusVisibility.pinned && !connectionStatusVisibility.focused) {
      syncConnectionStatusPopoverVisibility();
    }
  });

  connectionStatusAnchor?.addEventListener('focusin', () => {
    connectionStatusVisibility.focused = true;
    syncConnectionStatusPopoverVisibility();
  });

  connectionStatusAnchor?.addEventListener('focusout', (event) => {
    if (connectionStatusAnchor && event.relatedTarget && connectionStatusAnchor.contains(event.relatedTarget)) {
      return;
    }

    connectionStatusVisibility.focused = false;
    if (!connectionStatusVisibility.pinned && !connectionStatusVisibility.hovered) {
      syncConnectionStatusPopoverVisibility();
    }
  });

  connectionStatusAnchor?.addEventListener('click', (event) => {
    if (event.target !== connectionPill && event.target !== connectionStatusAnchor) {
      return;
    }

    connectionStatusVisibility.pinned = !connectionStatusVisibility.pinned;
    if (connectionStatusVisibility.pinned) {
      connectionStatusVisibility.focused = true;
    } else {
      connectionStatusVisibility.focused = false;
      if (!connectionStatusVisibility.hovered) {
        connectionStatusAnchor.blur();
      }
    }
    syncConnectionStatusPopoverVisibility();
    event.preventDefault();
  });

  connectionStatusAnchor?.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      connectionStatusVisibility.pinned = !connectionStatusVisibility.pinned;
      if (connectionStatusVisibility.pinned) {
        connectionStatusVisibility.focused = true;
      } else {
        connectionStatusVisibility.focused = false;
        if (!connectionStatusVisibility.hovered) {
          connectionStatusAnchor.blur();
        }
      }
      syncConnectionStatusPopoverVisibility();
    }

    if (event.key === 'Escape') {
      connectionStatusVisibility.pinned = false;
      connectionStatusVisibility.focused = false;
      syncConnectionStatusPopoverVisibility();
      connectionStatusAnchor.blur();
    }
  });

  document.addEventListener('click', (event) => {
    if (!connectionStatusVisibility.pinned || !connectionStatusAnchor) {
      return;
    }

    if (connectionStatusAnchor.contains(event.target)) {
      return;
    }

    connectionStatusVisibility.pinned = false;
    connectionStatusVisibility.hovered = false;
    connectionStatusVisibility.focused = false;
    syncConnectionStatusPopoverVisibility();
  });

  wsClient.addEventListener('connected', () => {
    updateConnectionStatus('connected');
  });

  wsClient.addEventListener('disconnected', () => {
    updateConnectionStatus('disconnected');
  });

  wsClient.addEventListener('error', () => {
    updateConnectionStatus('disconnected');
  });

  void hydrateConnectionStatusFromHealth();

  // Streaming Indicator
  function showStreaming() {
    if (currentAssistantMessage) {
      currentAssistantMessage.classList.add('streaming');
    }
  }

  function hideStreaming() {
    if (currentAssistantMessage) {
      currentAssistantMessage.classList.remove('streaming');
    }
  }

  // Message Handler
  function handleWebSocketMessage(msg) {
    switch (msg.type) {
      case 'chat.started':
        currentAssistantMessage = document.createElement('chat-message');
        currentAssistantMessage.setAttribute('role', 'assistant');
        currentAssistantMessage.setAttribute('content', '');
        currentAssistantMessage.setAttribute('timestamp', new Date().toISOString());
        currentAssistantMessage.setAttribute('message-id', msg.payload?.messageId || '');
        currentAssistantMessage.setAttribute('data-session-message', 'true');
        currentAssistantMessage.classList.add('streaming');
        messageList.appendChild(currentAssistantMessage);
        applyGlueShimmerEffect(currentAssistantMessage);
        showStreaming();
        scrollToBottom();
        break;

      case 'reasoning.chunk':
        if (currentAssistantMessage && msg.payload && msg.payload.content) {
          currentAssistantMessage.appendReasoning(msg.payload.content);
          playKidcoreChunk();
          pulseGlueShimmer(currentAssistantMessage);
          scrollToBottom();
        }
        break;

      case 'chat.chunk':
        if (currentAssistantMessage && msg.payload && msg.payload.content) {
          currentAssistantMessage.appendContent(msg.payload.content);
          playKidcoreChunk();
          pulseGlueShimmer(currentAssistantMessage);
          scrollToBottom();
        }
        break;

      case 'chat.complete':
        hideStreaming();
        playKidcoreMessageComplete();
        clearGlueShimmerEffect(currentAssistantMessage);
        currentAssistantMessage = null;
        activeToolCalls.clear();
        enableInput();
        // Add copy buttons to any new code blocks
        addCopyButtons();
        // Send next queued message if any
        processQueue();
        break;

      case 'chat.error':
        hideStreaming();
        playKidcoreError();
        showError(msg.payload?.error || 'An error occurred');
        clearGlueShimmerEffect(currentAssistantMessage);
        currentAssistantMessage = null;
        activeToolCalls.clear();
        enableInput();
        break;

      case 'session.new':
        handleSessionNew(msg.payload);
        break;

      case 'session.loaded':
        handleSessionLoaded(msg.payload);
        break;

      case 'session.list':
        handleSessionList(msg.payload);
        break;

      case 'session.info':
        handleSessionInfo(msg.payload);
        break;

      case 'context.info':
        handleContextInfo(msg.payload);
        break;

      case 'tool.start':
        handleToolStart(msg.payload);
        break;

      case 'tool.output':
        handleToolOutput(msg.payload);
        break;

      case 'tool.end':
        handleToolEnd(msg.payload);
        break;

      case 'completion.suggestions':
        showCompletionMenu(msg.payload?.suggestions || []);
        break;

      case 'status.update':
        updateStatusBar(msg.payload);
        break;

      case 'toast':
        showToast(msg.payload?.message, msg.payload?.level);
        break;

      default:
        console.log('Unhandled message type:', msg.type);
    }
  }

  wsClient.addEventListener('message', (event) => {
    handleWebSocketMessage(event.detail);
  });

  if (typeof window !== 'undefined') {
    window.__alfredWebUI = {
      emitMessage: handleWebSocketMessage,
      syncKidcoreAudioControls,
      getCurrentAssistantMessage: () => currentAssistantMessage,
    };
  }

  // Session Handlers
  function handleSessionNew(payload) {
    // Clear message list and history for new session
    messageList.innerHTML = '';
    messageHistory.length = 0;
    historyIndex = -1;
    currentAssistantMessage = null;
    activeToolCalls.clear();
    activeSessionId = payload.sessionId || null;
    showSystemMessage(`New session created: ${payload.sessionId}`);
    enableInput();
  }

  function handleSessionLoaded(payload) {
    reconcileSessionLoaded(payload);
    showSystemMessage(`Session resumed: ${payload.sessionId}`);
    addCopyButtons();
    enableInput();
  }

  function handleSessionList(payload) {
    const sessions = payload.sessions || [];

    if (sessions.length === 0) {
      showSystemMessage('No recent sessions found.');
      enableInput();
      return;
    }

    // Create session list container (not using chat-message to avoid re-render issues)
    const container = document.createElement('div');
    container.className = 'session-list-message';

    // Create and append the session list component
    const sessionList = document.createElement('session-list');
    sessionList.setAttribute('sessions', JSON.stringify(sessions));

    // Listen for session selection
    sessionList.addEventListener('session-select', (e) => {
      const sessionId = e.detail.sessionId;
      if (sessionId) {
        wsClient.sendCommand(`/resume ${sessionId}`);
      }
    });

    container.appendChild(sessionList);
    messageList.appendChild(container);

    scrollToBottom();
    enableInput();
  }

  function handleSessionInfo(payload) {
    let content = 'Current Session:\n\n';
    content += `ID: ${payload.sessionId}\n`;
    content += `Status: ${payload.status || 'unknown'}\n`;
    content += `Messages: ${payload.messageCount}\n`;
    if (payload.created) {
      content += `Created: ${new Date(payload.created).toLocaleString()}\n`;
    }
    if (payload.lastActive) {
      content += `Last Active: ${new Date(payload.lastActive).toLocaleString()}\n`;
    }

    showSystemMessage(content);
    enableInput();
  }

  function handleContextInfo(payload) {
    const warnings = Array.isArray(payload.warnings) ? payload.warnings.filter(Boolean) : [];
    const blockedContextFiles = Array.isArray(payload.blockedContextFiles)
      ? payload.blockedContextFiles.filter(Boolean)
      : [];

    if (!warnings.length && blockedContextFiles.length > 0) {
      warnings.push(`Blocked context files: ${blockedContextFiles.join(', ')}`);
    }

    const lines = [];

    if (warnings.length > 0) {
      lines.push('WARNING:');
      warnings.forEach(warning => {
        lines.push(`  ! ${warning}`);
      });
      lines.push('');
    }

    lines.push('System Context:', '');

    if (payload.systemPrompt) {
      lines.push(`System Prompt: ${payload.systemPrompt.totalTokens || 0} tokens`);
      const sections = payload.systemPrompt.sections || [];
      sections.forEach(section => {
        lines.push(`  - ${section.name}: ${section.tokens} tokens`);
      });
      lines.push('');
    }

    if (payload.memories) {
      lines.push(
        `Memories: ${payload.memories.displayed || 0} shown / ${payload.memories.total || 0} total (${payload.memories.tokens || 0} tokens)`
      );
      lines.push('');
    }

    if (payload.sessionHistory) {
      lines.push(
        `Session History: ${payload.sessionHistory.count || 0} messages (${payload.sessionHistory.tokens || 0} tokens)`
      );
      lines.push('');
    }

    if (payload.toolCalls) {
      lines.push(`Tool Calls: ${payload.toolCalls.count || 0} (${payload.toolCalls.tokens || 0} tokens)`);
      lines.push('');
    }

    lines.push(`Total Tokens: ${payload.totalTokens || 0}`);

    showSystemMessage(lines.join('\n'), { warning: warnings.length > 0 });
    enableInput();
  }

  function showSystemMessage(content, options = {}) {
    const systemMsg = document.createElement('chat-message');
    systemMsg.setAttribute('role', 'system');
    systemMsg.setAttribute('content', content);
    if (options.warning) {
      systemMsg.setAttribute('data-warning', 'true');
    } else {
      systemMsg.removeAttribute('data-warning');
    }
    messageList.appendChild(systemMsg);
    scrollToBottom();
  }

  // Tool Call Handlers
  function handleToolStart(payload) {
    if (!currentAssistantMessage) return;

    const toolCall = document.createElement('tool-call');
    toolCall.setAttribute('tool-call-id', payload.toolCallId);
    toolCall.setAttribute('tool-name', payload.toolName);
    toolCall.setAttribute('arguments', JSON.stringify(payload.arguments || {}));
    toolCall.setAttribute('status', 'running');
    toolCall.setAttribute('expanded', 'true');

    activeToolCalls.set(payload.toolCallId, toolCall);
    currentAssistantMessage.appendToolCall(toolCall);
    scrollToBottom();
  }

  function handleToolOutput(payload) {
    const toolCall = activeToolCalls.get(payload.toolCallId);
    if (toolCall) {
      toolCall.appendOutput(payload.chunk);
      scrollToBottom();
    }
  }

  function handleToolEnd(payload) {
    const toolCall = activeToolCalls.get(payload.toolCallId);
    if (toolCall) {
      toolCall.setStatus(payload.success ? 'success' : 'error');
      if (payload.output) {
        toolCall.setAttribute('output', payload.output);
      }
      toolCall.collapse();
      if (!payload.success) {
        playKidcoreError();
        showError(`Tool ${toolCall.getToolName()} failed`);
      }
      scrollToBottom();
    }
  }

  // Queue Management
  function addToQueue(content) {
    messageQueue.push(content);
    updateQueueBadge();
    showToast(`Message queued (${messageQueue.length})`, 'info');
  }

  function processQueue() {
    if (messageQueue.length > 0 && !currentAssistantMessage) {
      const content = messageQueue.shift();
      updateQueueBadge();
      sendMessageContent(content);
    }
  }

  function updateQueueBadge() {
    queueBadge.textContent = messageQueue.length;
    if (messageQueue.length === 0) {
      queueBadge.classList.add('hidden');
    } else {
      queueBadge.classList.remove('hidden');
    }
  }

  function clearQueue() {
    messageQueue.length = 0;
    updateQueueBadge();
    showToast('Queue cleared', 'info');
  }

  // Message History
  function addToHistory(content) {
    messageHistory.push(content);
    historyIndex = messageHistory.length;
  }

  function navigateHistory(direction) {
    if (messageHistory.length === 0) return;

    if (direction === 'up') {
      historyIndex = Math.max(0, historyIndex - 1);
    } else {
      historyIndex = Math.min(messageHistory.length, historyIndex + 1);
    }

    if (historyIndex < messageHistory.length) {
      messageInput.value = messageHistory[historyIndex];
    } else {
      messageInput.value = '';
    }

    autoResizeTextarea();
  }

  // Send Message
  function sendMessage() {
    const content = messageInput.value.trim();
    if (!content) return;

    sendMessageContent(content);
    messageInput.value = '';
    autoResizeTextarea();
  }

  function sendMessageContent(content) {
    // Add to history
    addToHistory(content);
    playKidcoreSend();

    // Send via WebSocket - commands use command.execute, chat uses chat.send
    if (content.startsWith('/')) {
      pendingKidcoreStreamingFx = null;

      // Commands: show as system message, don't disable input
      const cmdMsg = document.createElement('chat-message');
      cmdMsg.setAttribute('role', 'system');
      cmdMsg.setAttribute('content', `Command: ${content}`);
      cmdMsg.setAttribute('timestamp', new Date().toISOString());
      messageList.appendChild(cmdMsg);
      scrollToBottom();

      wsClient.sendCommand(content);
      // Don't disable input - commands are instant
    } else {
      pendingKidcoreStreamingFx = content.toLowerCase().includes('glue shimmer') ? 'glue-shimmer' : null;

      // Chat messages: show as user message, disable input during streaming
      const userMessage = document.createElement('chat-message');
      userMessage.setAttribute('role', 'user');
      userMessage.setAttribute('content', content);
      userMessage.setAttribute('timestamp', new Date().toISOString());
      userMessage.setAttribute('data-session-message', 'true');
      messageList.appendChild(userMessage);

      disableInput();
      scrollToBottom();

      wsClient.sendChat(content);
    }
  }

  function findPreviousUserPrompt(messageElement) {
    let previousMessage = messageElement?.previousElementSibling ?? null;

    while (previousMessage) {
      if (
        previousMessage.matches?.('chat-message') &&
        previousMessage.getAttribute('role') === 'user'
      ) {
        return typeof previousMessage.getContent === 'function'
          ? previousMessage.getContent()
          : previousMessage.getAttribute('content') || '';
      }

      previousMessage = previousMessage.previousElementSibling ?? null;
    }

    return '';
  }

  function retryAssistantMessage(messageElement) {
    if (currentAssistantMessage) {
      showError('Wait for the current response to finish before regenerating.');
      return;
    }

    const previousPrompt = findPreviousUserPrompt(messageElement);
    if (!previousPrompt) {
      showError('Could not find the previous user prompt to regenerate this reply.');
      return;
    }

    sendMessageContent(previousPrompt);
  }

  // Textarea Auto-Resize
  function autoResizeTextarea() {
    messageInput.style.height = 'auto';
    const newHeight = Math.min(messageInput.scrollHeight, 200);
    messageInput.style.height = `${newHeight}px`;
  }

  // Command Completion
  function showCompletionMenu(items) {
    if (items.length === 0) {
      completionMenu.hide();
      return;
    }
    completionMenu.setItems(items);
    completionMenu.show();
  }

  function checkForCompletionTrigger() {
    const value = messageInput.value;
    const cursorPosition = messageInput.selectionStart;

    // Get text before cursor
    const textBeforeCursor = value.substring(0, cursorPosition);
    const lines = textBeforeCursor.split('\n');
    const currentLine = lines[lines.length - 1];

    // Check if we're at the start of a command
    if (currentLine.startsWith('/')) {
      const filter = currentLine.substring(1);
      const filtered = commands.filter(cmd =>
        cmd.value.toLowerCase().includes(filter.toLowerCase()) ||
        (cmd.description && cmd.description.toLowerCase().includes(filter.toLowerCase()))
      );
      showCompletionMenu(filtered);
    } else {
      completionMenu.hide();
    }
  }

  // Global Tool Toggle (Ctrl+T)
  function toggleAllTools() {
    allToolsExpanded = !allToolsExpanded;
    const toolCalls = document.querySelectorAll('tool-call');
    toolCalls.forEach(tool => {
      if (allToolsExpanded) {
        tool.expand();
      } else {
        tool.collapse();
      }
    });
  }

  // UI Helpers
  function disableInput() {
    messageInput.disabled = true;
    sendButton.disabled = true;
  }

  function enableInput() {
    messageInput.disabled = false;
    sendButton.disabled = false;
    messageInput.focus();
  }

  function scrollToBottom() {
    chatContainer.scrollTop = chatContainer.scrollHeight;
  }

  function showError(message) {
    const errorMsg = document.createElement('chat-message');
    errorMsg.setAttribute('role', 'system');
    errorMsg.setAttribute('content', `Error: ${message}`);
    messageList.appendChild(errorMsg);
    scrollToBottom();
  }

  // Toast notification
  function showToast(message, level = 'info') {
    playKidcoreClick();
    const toastContainer = document.getElementById('toast-container');
    if (toastContainer && toastContainer.show) {
      toastContainer.show(message, level, 5000);
    } else {
      console.log(`[${level?.toUpperCase() || 'INFO'}] ${message}`);
    }
  }

  // Status Bar Update
  function updateStatusBar(payload) {
    const statusBar = document.getElementById('status-bar');
    if (!statusBar) return;

    // Update model
    if (payload.model !== undefined) {
      statusBar.setAttribute('model', payload.model);
    }

    // Update tokens
    if (payload.inputTokens !== undefined || payload.outputTokens !== undefined) {
      statusBar.setAttribute('inputtokens', payload.inputTokens || 0);
      statusBar.setAttribute('outputtokens', payload.outputTokens || 0);
      if (payload.cacheReadTokens !== undefined) {
        statusBar.setAttribute('cachedtokens', payload.cacheReadTokens);
      }
      if (payload.reasoningTokens !== undefined) {
        statusBar.setAttribute('reasoningtokens', payload.reasoningTokens);
      }
      if (payload.contextTokens !== undefined) {
        statusBar.setAttribute('contexttokens', payload.contextTokens);
      }
    }

    // Update queue
    if (payload.queueLength !== undefined) {
      statusBar.setAttribute('queue', payload.queueLength);
    }

    // Update streaming status
    if (payload.isStreaming !== undefined) {
      statusBar.setAttribute('streaming', payload.isStreaming);
    }

    applyDaemonStatusPayload(payload);
  }

  // Event Listeners
  sendButton.addEventListener('click', sendMessage);

  // History navigation buttons (mobile)
  const historyUpBtn = document.getElementById('history-up');
  const historyDownBtn = document.getElementById('history-down');
  historyUpBtn?.addEventListener('click', () => navigateHistory('up'));
  historyDownBtn?.addEventListener('click', () => navigateHistory('down'));

  // Textarea input handling
  messageInput.addEventListener('input', () => {
    autoResizeTextarea();
    checkForCompletionTrigger();
  });

  // Keyboard handling
  messageInput.addEventListener('keydown', (e) => {
    // Handle completion menu first (before other Enter handling)
    if (completionMenu.isVisible()) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        completionMenu.selectNext();
        return;
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        completionMenu.selectPrevious();
        return;
      }
      if (e.key === 'Enter' || e.key === 'Tab') {
        e.preventDefault();
        completionMenu.selectCurrent();
        return;
      }
      if (e.key === 'Escape') {
        completionMenu.hide();
        return;
      }
    }

    // Shift+Enter: Queue message
    if (e.key === 'Enter' && e.shiftKey) {
      e.preventDefault();
      const content = messageInput.value.trim();
      if (content) {
        addToQueue(content);
        messageInput.value = '';
        autoResizeTextarea();
      }
      return;
    }

    // Enter (without Shift): Send message
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
      return;
    }

    // History navigation
    if (e.key === 'ArrowUp' && messageInput.selectionStart === 0) {
      e.preventDefault();
      navigateHistory('up');
      return;
    }
    if (e.key === 'ArrowDown' && messageInput.selectionStart === messageInput.value.length) {
      e.preventDefault();
      navigateHistory('down');
      return;
    }

    // Ctrl+U: Clear input
    if (e.ctrlKey && e.key === 'u') {
      e.preventDefault();
      messageInput.value = '';
      autoResizeTextarea();
      return;
    }
  });

  // Global keyboard shortcuts
  document.addEventListener('keydown', (e) => {
    // Ctrl+T: Toggle all tool calls
    if (e.ctrlKey && e.key === 't') {
      e.preventDefault();
      toggleAllTools();
      return;
    }

    // Escape: Clear queue
    if (e.key === 'Escape' && messageQueue.length > 0) {
      clearQueue();
    }
  });

  messageList.addEventListener('retry-message', (event) => {
    const messageElement = event.target?.closest?.('chat-message');
    if (!messageElement || messageElement.getAttribute('role') !== 'assistant') {
      return;
    }

    retryAssistantMessage(messageElement);
  });

  // Completion menu selection
  completionMenu.addEventListener('select', (e) => {
    const selected = e.detail;
    const value = messageInput.value;
    const cursorPosition = messageInput.selectionStart;

    // Replace current command with selected one
    const textBeforeCursor = value.substring(0, cursorPosition);
    const lines = textBeforeCursor.split('\n');
    const currentLineIndex = lines.length - 1;
    const currentLine = lines[currentLineIndex];

    if (currentLine.startsWith('/')) {
      lines[currentLineIndex] = selected.value + ' ';
      const newTextBefore = lines.join('\n');
      const newValue = newTextBefore + value.substring(cursorPosition);

      messageInput.value = newValue;
      const newCursorPos = newTextBefore.length;
      messageInput.setSelectionRange(newCursorPos, newCursorPos);
      messageInput.focus();
    }

    completionMenu.hide();
  });

  // Auto-scroll on window resize
  window.addEventListener('resize', scrollToBottom);

  // Connect WebSocket
  wsClient.connect();

  // Focus input on load
  messageInput.focus();

  console.log('Alfred Web UI initialized');
}

// Add copy buttons to code blocks
function addCopyButtons() {
  const codeBlocks = document.querySelectorAll('pre code');
  codeBlocks.forEach((codeBlock) => {
    // Skip if already wrapped
    if (codeBlock.closest('.code-block-wrapper')) return;

    const pre = codeBlock.parentElement;
    const wrapper = document.createElement('div');
    wrapper.className = 'code-block-wrapper';

    // Create copy button - same icon as message copy
    const copyBtn = document.createElement('button');
    copyBtn.className = 'code-copy-btn';
    copyBtn.innerHTML = '⧉';
    copyBtn.title = 'Copy code';

    copyBtn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const textToCopy = codeBlock.textContent;

      // Try modern clipboard API first
      if (navigator.clipboard && navigator.clipboard.writeText) {
        try {
          await navigator.clipboard.writeText(textToCopy);
          showCopyFeedback(copyBtn);
          return;
        } catch (err) {
          console.log('Clipboard API failed, trying fallback');
        }
      }

      // Fallback: use execCommand
      try {
        const textarea = document.createElement('textarea');
        textarea.value = textToCopy;
        textarea.style.position = 'fixed';
        textarea.style.left = '-9999px';
        textarea.style.top = '0';
        document.body.appendChild(textarea);
        textarea.focus();
        textarea.select();

        const successful = document.execCommand('copy');
        document.body.removeChild(textarea);

        if (successful) {
          showCopyFeedback(copyBtn);
        } else {
          console.error('execCommand copy failed');
          showCopyFailed(copyBtn);
        }
      } catch (err) {
        console.error('Failed to copy:', err);
        showCopyFailed(copyBtn);
      }
    });

    // Wrap the pre element
    pre.parentNode.insertBefore(wrapper, pre);
    wrapper.appendChild(copyBtn);
    wrapper.appendChild(pre);
  });
}

function showCopyFeedback(btn) {
  if (!btn) return;
  const originalText = btn.innerHTML;
  btn.innerHTML = '✓';
  btn.classList.add('copied');
  setTimeout(() => {
    btn.innerHTML = originalText;
    btn.classList.remove('copied');
  }, 800);
}

function showCopyFailed(btn) {
  if (!btn) return;
  const originalText = btn.innerHTML;
  btn.innerHTML = '✗';
  btn.classList.add('failed');
  setTimeout(() => {
    btn.innerHTML = originalText;
    btn.classList.remove('failed');
  }, 1500);
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initAlfredUI);
} else {
  initAlfredUI();
}
