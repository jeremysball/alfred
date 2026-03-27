// Alfred Web UI - Main JavaScript
import { applyThemeContrast } from './utils/contrast.js';

// Mobile Chrome Collapse
const MOBILE_BREAKPOINT = 768;
let isChromeCollapsed = false;

function handleScroll() {
  if (window.innerWidth <= MOBILE_BREAKPOINT) {
    const scrollTop = window.scrollY || document.documentElement.scrollTop;
    if (scrollTop > 50 && !isChromeCollapsed) {
      collapseChrome();
    } else if (scrollTop <= 50 && isChromeCollapsed) {
      restoreChrome();
    }
  }
}

function collapseChrome() {
  isChromeCollapsed = true;
  const header = document.querySelector('.app-header');
  const inputArea = document.querySelector('.input-area');
  if (header) header.classList.add('compact');
  if (inputArea) inputArea.classList.add('compact');
}

function restoreChrome() {
  isChromeCollapsed = false;
  const header = document.querySelector('.app-header');
  const inputArea = document.querySelector('.input-area');
  if (header) header.classList.remove('compact');
  if (inputArea) inputArea.classList.remove('compact');
}

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
  const stopButton = document.getElementById('stop-button');
  const connectionPill = document.getElementById('connection-pill');
  const connectionStatusAnchor = document.getElementById('connection-status-anchor');
  const connectionStatusTooltip = document.getElementById('connection-status-tooltip');
  const chatContainer = document.getElementById('chat-container');
  const queueBadge = document.getElementById('queue-badge');
  const inputArea = document.getElementById('input-area');

  const completionMenu = document.getElementById('completion-menu');

  // Reset composer state on load to prevent stale streaming UI
  if (inputArea) {
    inputArea.dataset.composerState = 'idle';
  }
  if (stopButton) {
    stopButton.hidden = true;
    stopButton.disabled = false;
    stopButton.style.opacity = '';
  }

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
      setMessageState(messageEl, 'streaming');
    } else {
      setMessageState(messageEl, 'idle');
    }

    // Handle interleaved reasoning blocks (new format) or legacy reasoningContent
    if (role === 'assistant') {
      if (Array.isArray(msg.reasoningBlocks) && msg.reasoningBlocks.length > 0) {
        // New format: interleaved reasoning blocks with sequences
        messageEl.setReasoningBlocks(msg.reasoningBlocks);
      } else if (loadedReasoning || !preserveExistingAssistantContent) {
        // Legacy format: single reasoning string
        if (!preserveExistingAssistantContent || loadedReasoning.length >= existingReasoning.length) {
          messageEl.setReasoning(loadedReasoning);
        }
      }
    }

    if (Array.isArray(msg.toolCalls) && (msg.toolCalls.length > 0 || !preserveExistingAssistantContent)) {
      // Sort tool calls by sequence to preserve original ordering
      const sortedToolCalls = [...msg.toolCalls].sort((a, b) => {
        const seqA = a.sequence !== undefined ? a.sequence : 0;
        const seqB = b.sequence !== undefined ? b.sequence : 0;
        return seqA - seqB;
      });
      messageEl.setToolCalls(sortedToolCalls);
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
    // This prevents duplication of loading indicators, toasts, etc.
    Array.from(messageList.children).forEach((child) => {
      // Keep chat-message elements (they're handled below)
      if (child.matches?.('chat-message')) {
        return;
      }
      // Remove all other ephemeral elements
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

    // Remove messages that are no longer in the incoming set
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

    let nextCurrentAssistantMessage = null;
    let lastElement = null;

    messages.forEach((msg, index) => {
      const messageId = getSessionMessageId(msg, index);
      let messageEl = existingById.get(messageId) || null;

      if (messageEl) {
        // Update existing message and move it to the correct position
        applySessionMessageState(messageEl, msg, {
          preserveExistingAssistantContent: messageEl === currentAssistantMessage,
        });
      } else {
        // Create new message element
        messageEl = document.createElement('chat-message');
        applySessionMessageState(messageEl, msg);
      }

      // Always append to ensure correct order (moves existing, appends new)
      messageList.appendChild(messageEl);
      lastElement = messageEl;

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
      messageList.appendChild(currentAssistantMessage);
      nextCurrentAssistantMessage = currentAssistantMessage;
    }

    currentAssistantMessage = nextCurrentAssistantMessage;
    activeSessionId = incomingSessionId;
    historyIndex = messageHistory.length;
    refreshEditableMessageState();
  }

  // WebSocket Client
  const wsClient = new AlfredWebSocketClient();
  let currentAssistantMessage = null;
  let activeSessionId = null;
  let pendingEditRequest = null;
  let pendingChatSendRequest = null;
  let composerState = 'idle';
  let editingMessageElement = null;
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
    { value: '/context', description: 'Show system context (use /context toggle <section> [on|off])' },
    { value: '/debug', description: 'Show debug diagnostics (all|session|messages|websocket)' },
    { value: '/help', description: 'Show available commands' }
  ];

  // Connection Status Handler
  const CONNECTION_STATUS_MOBILE_BREAKPOINT = 769;
  const CONNECTION_STATUS_PORTAL_ROOT_ID = 'connection-status-portal-root';
  const CONNECTION_STATUS_VIEWPORT_PADDING = 12;
  const CONNECTION_STATUS_TRIGGER_OVERLAP = 4;

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

  function ensureConnectionStatusPortalRoot() {
    let portalRoot = document.getElementById(CONNECTION_STATUS_PORTAL_ROOT_ID);
    if (!portalRoot) {
      portalRoot = document.createElement('div');
      portalRoot.id = CONNECTION_STATUS_PORTAL_ROOT_ID;
      portalRoot.className = 'connection-status-portal-root';
      portalRoot.setAttribute('aria-hidden', 'true');
      document.body.appendChild(portalRoot);
    }

    let overlay = portalRoot.querySelector('.connection-status-overlay');
    if (!overlay) {
      overlay = document.createElement('div');
      overlay.className = 'connection-status-overlay';
      overlay.setAttribute('aria-hidden', 'true');
      portalRoot.appendChild(overlay);
    }

    if (connectionStatusTooltip && connectionStatusTooltip.parentElement !== portalRoot) {
      portalRoot.appendChild(connectionStatusTooltip);
    }

    return portalRoot;
  }

  const connectionStatusPortalRoot = ensureConnectionStatusPortalRoot();
  const connectionStatusOverlay = connectionStatusPortalRoot?.querySelector('.connection-status-overlay');

  function isConnectionStatusHoverTarget(target) {
    if (!target) {
      return false;
    }

    return Boolean(
      (connectionStatusAnchor && connectionStatusAnchor.contains(target)) ||
      (connectionStatusTooltip && connectionStatusTooltip.contains(target))
    );
  }

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

  function refreshConnectionStatusTooltip() {
    renderConnectionStatusTooltip();
    positionConnectionStatusTooltip();
  }

  function startConnectionStatusRefreshTimer() {
    if (connectionStatusRefreshTimer !== null) {
      return;
    }

    connectionStatusRefreshTimer = window.setInterval(() => {
      if (isConnectionStatusOpen()) {
        refreshConnectionStatusTooltip();
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

  function positionConnectionStatusTooltip() {
    if (!connectionStatusPortalRoot || !connectionStatusTooltip || !connectionStatusAnchor || !connectionPill) {
      return;
    }

    const isOpen = isConnectionStatusOpen();
    const isMobileLayout = window.innerWidth < CONNECTION_STATUS_MOBILE_BREAKPOINT;

    connectionStatusPortalRoot.dataset.layout = isMobileLayout ? 'sheet' : 'popover';
    connectionStatusPortalRoot.dataset.open = String(isOpen);
    connectionStatusPortalRoot.setAttribute('aria-hidden', String(!isOpen));
    connectionStatusTooltip.setAttribute('aria-hidden', String(!isOpen));
    connectionStatusAnchor.dataset.open = String(isOpen);
    connectionStatusAnchor.dataset.pinned = String(connectionStatusVisibility.pinned);
    connectionStatusAnchor.setAttribute('aria-expanded', String(isOpen));
    connectionPill.setAttribute('aria-expanded', String(isOpen));

    if (!isOpen) {
      return;
    }

    if (isMobileLayout) {
      connectionStatusTooltip.style.top = 'auto';
      connectionStatusTooltip.style.right = '0';
      connectionStatusTooltip.style.bottom = '0';
      connectionStatusTooltip.style.left = '0';
      return;
    }

    connectionStatusTooltip.style.top = '0px';
    connectionStatusTooltip.style.right = 'auto';
    connectionStatusTooltip.style.bottom = 'auto';
    connectionStatusTooltip.style.left = '0px';

    const anchorRect = connectionStatusAnchor.getBoundingClientRect();
    const tooltipRect = connectionStatusTooltip.getBoundingClientRect();
    const maxLeft = Math.max(
      CONNECTION_STATUS_VIEWPORT_PADDING,
      window.innerWidth - tooltipRect.width - CONNECTION_STATUS_VIEWPORT_PADDING,
    );
    const left = Math.min(Math.max(anchorRect.left, CONNECTION_STATUS_VIEWPORT_PADDING), maxLeft);
    const maxTop = Math.max(
      CONNECTION_STATUS_VIEWPORT_PADDING,
      window.innerHeight - tooltipRect.height - CONNECTION_STATUS_VIEWPORT_PADDING,
    );
    const top = Math.min(
      Math.max(anchorRect.bottom - CONNECTION_STATUS_TRIGGER_OVERLAP, CONNECTION_STATUS_VIEWPORT_PADDING),
      maxTop,
    );

    connectionStatusTooltip.style.left = `${Math.round(left)}px`;
    connectionStatusTooltip.style.top = `${Math.round(top)}px`;
  }

  function syncConnectionStatusPopoverVisibility() {
    if (!connectionStatusPortalRoot || !connectionStatusTooltip || !connectionPill) {
      return;
    }

    const isOpen = isConnectionStatusOpen();
    connectionStatusPortalRoot.dataset.open = String(isOpen);
    connectionStatusAnchor.dataset.open = String(isOpen);
    connectionStatusAnchor.dataset.pinned = String(connectionStatusVisibility.pinned);
    connectionStatusAnchor.setAttribute('aria-expanded', String(isOpen));
    connectionStatusTooltip.setAttribute('aria-hidden', String(!isOpen));
    connectionPill.setAttribute('aria-expanded', String(isOpen));

    refreshConnectionStatusTooltip();

    if (isOpen) {
      startConnectionStatusRefreshTimer();
    } else {
      stopConnectionStatusRefreshTimer();
    }
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

    syncConnectionStatusPopoverVisibility();
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
    syncConnectionStatusPopoverVisibility();
  }

  connectionStatusAnchor?.addEventListener('pointerenter', () => {
    connectionStatusVisibility.hovered = true;
    syncConnectionStatusPopoverVisibility();
  });

  connectionStatusAnchor?.addEventListener('pointerleave', (event) => {
    if (isConnectionStatusHoverTarget(event.relatedTarget)) {
      return;
    }

    connectionStatusVisibility.hovered = false;
    if (!connectionStatusVisibility.pinned && !connectionStatusVisibility.focused) {
      syncConnectionStatusPopoverVisibility();
    }
  });

  connectionStatusTooltip?.addEventListener('pointerenter', () => {
    connectionStatusVisibility.hovered = true;
    syncConnectionStatusPopoverVisibility();
  });

  connectionStatusTooltip?.addEventListener('pointerleave', (event) => {
    if (isConnectionStatusHoverTarget(event.relatedTarget)) {
      return;
    }

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
    if (!connectionStatusAnchor.contains(event.target)) {
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

  connectionStatusOverlay?.addEventListener('click', () => {
    connectionStatusVisibility.pinned = false;
    connectionStatusVisibility.hovered = false;
    connectionStatusVisibility.focused = false;
    syncConnectionStatusPopoverVisibility();
    connectionStatusAnchor?.blur();
  });

  document.addEventListener('click', (event) => {
    if (!connectionStatusVisibility.pinned || !connectionStatusAnchor || !connectionStatusPortalRoot) {
      return;
    }

    if (connectionStatusAnchor.contains(event.target) || connectionStatusPortalRoot.contains(event.target)) {
      return;
    }

    connectionStatusVisibility.pinned = false;
    connectionStatusVisibility.hovered = false;
    connectionStatusVisibility.focused = false;
    syncConnectionStatusPopoverVisibility();
  });

  window.addEventListener('resize', () => {
    if (!connectionStatusPortalRoot) {
      return;
    }

    positionConnectionStatusTooltip();
  }, { passive: true });

  wsClient.addEventListener('connected', () => {
    updateConnectionStatus('connected');
  });

  wsClient.addEventListener('disconnected', () => {
    updateConnectionStatus('disconnected');
    // Always clean up on disconnect to ensure consistent state
    // Remove partial assistant message since we can't recover the stream
    if (currentAssistantMessage) {
      clearCurrentAssistantMessage({ remove: true });
    }
    // Reset composer state to idle
    setComposerState('idle');
    // Reset stop button
    if (stopButton) {
      stopButton.hidden = true;
      stopButton.disabled = false;
      stopButton.style.opacity = '';
    }
    // Clear any queued messages since we can't send them
    messageQueue.length = 0;
    updateQueueBadge();
    // Refresh editable state
    refreshEditableMessageState();
    // Ensure input is enabled
    if (messageInput) {
      messageInput.disabled = false;
    }
    if (sendButton) {
      sendButton.disabled = false;
    }
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

  function clearCurrentAssistantMessage({ remove = false } = {}) {
    const assistantMessage = currentAssistantMessage;
    if (!assistantMessage) {
      return null;
    }

    hideStreaming();
    assistantMessage.classList.remove('cancelling');
    clearGlueShimmerEffect(assistantMessage);
    if (remove) {
      assistantMessage.remove();
    } else if (typeof assistantMessage.setMessageState === 'function') {
      assistantMessage.setMessageState('idle');
    } else {
      assistantMessage.classList.remove('streaming', 'editing');
      assistantMessage.dataset.messageState = 'idle';
    }

    currentAssistantMessage = null;
    activeToolCalls.clear();
    return assistantMessage;
  }

  function setMessageState(messageElement, state) {
    if (!messageElement) {
      return;
    }

    if (typeof messageElement.setMessageState === 'function') {
      messageElement.setMessageState(state);
      return;
    }

    const nextState = state === 'streaming' || state === 'editing' ? state : 'idle';
    messageElement.dataset.messageState = nextState;
    messageElement.classList.toggle('streaming', nextState === 'streaming');
    messageElement.classList.toggle('editing', nextState === 'editing');
  }

  function setComposerState(state) {
    const nextState = state === 'streaming' || state === 'editing' ? state : 'idle';
    composerState = nextState;
    if (inputArea) {
      inputArea.dataset.composerState = nextState;
    }
    // Update placeholder based on state
    if (messageInput) {
      if (nextState === 'editing') {
        messageInput.placeholder = 'Editing message... (Esc to cancel)';
      } else {
        messageInput.placeholder = 'Type your message... (Shift+Enter to queue)';
      }
    }
  }

  function createClientMessageId(prefix) {
    if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
      return `${prefix}-${crypto.randomUUID()}`;
    }

    return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
  }

  function refreshEditableMessageState() {
    const userMessages = Array.from(
      messageList.querySelectorAll('chat-message[data-session-message="true"]')
    ).filter((messageElement) => messageElement.getAttribute('role') === 'user');
    const lastUserMessage = userMessages[userMessages.length - 1] || null;
    const hasActiveStreamingTurn = composerState === 'streaming' || Boolean(currentAssistantMessage?.classList.contains('streaming'));

    if (currentAssistantMessage) {
      setMessageState(currentAssistantMessage, currentAssistantMessage.classList.contains('streaming') ? 'streaming' : 'idle');
    }

    userMessages.forEach((messageElement) => {
      const shouldBeEditable = !hasActiveStreamingTurn && messageElement === lastUserMessage;
      const nextState = messageElement === editingMessageElement ? 'editing' : 'idle';
      if (typeof messageElement.setEditable === 'function') {
        if (messageElement.getEditable?.() !== shouldBeEditable) {
          messageElement.setEditable(shouldBeEditable);
        }
      } else if (shouldBeEditable) {
        messageElement.setAttribute('editable', 'true');
      } else {
        messageElement.removeAttribute('editable');
      }
      setMessageState(messageElement, nextState);
    });

    if (editingMessageElement && !userMessages.includes(editingMessageElement)) {
      setMessageState(editingMessageElement, 'editing');
    }
  }

  function clearComposerEditState() {
    const previousEditingMessage = editingMessageElement;
    const wasEditing = previousEditingMessage !== null;
    if (previousEditingMessage) {
      setMessageState(previousEditingMessage, 'idle');
    }
    editingMessageElement = null;
    if (inputArea) {
      inputArea.removeAttribute('data-edit-message-id');
    }
    if (wasEditing) {
      messageInput.value = '';
      autoResizeTextarea();
    }
    refreshEditableMessageState();
  }

  function removeSessionMessagesAfter(messageElement) {
    let sibling = messageElement?.nextElementSibling ?? null;
    while (sibling) {
      const nextSibling = sibling.nextElementSibling;
      if (sibling.matches?.('chat-message[data-session-message="true"]')) {
        if (sibling === currentAssistantMessage) {
          currentAssistantMessage = null;
        }
        sibling.remove();
      }
      sibling = nextSibling;
    }
    activeToolCalls.clear();
  }

  function startComposerEdit(messageElement) {
    if (!messageElement || messageElement.getAttribute('role') !== 'user') {
      return;
    }

    const messageId = messageElement.getAttribute('message-id') || '';
    if (!messageId) {
      return;
    }

    const content = typeof messageElement.getContent === 'function'
      ? messageElement.getContent()
      : messageElement.getAttribute('content') || '';

    pendingEditRequest = null;
    clearComposerEditState();
    editingMessageElement = messageElement;
    setMessageState(messageElement, 'editing');
    if (inputArea) {
      inputArea.dataset.editMessageId = messageId;
    }

    messageInput.value = content;
    autoResizeTextarea();
    enableInput();
    setComposerState('editing');
    refreshEditableMessageState();
    messageInput.focus();
    messageInput.setSelectionRange(content.length, content.length);
  }

  function getRetryRequest(messageElement) {
    const previousUserMessage = findPreviousUserMessage(messageElement);
    if (!previousUserMessage) {
      return null;
    }

    const previousPrompt = typeof previousUserMessage.getContent === 'function'
      ? previousUserMessage.getContent()
      : previousUserMessage.getAttribute('content') || '';
    const messageId = previousUserMessage.getAttribute('message-id') || '';

    if (!previousPrompt || !messageId) {
      return null;
    }

    return {
      messageId,
      content: previousPrompt,
    };
  }

  function findPreviousUserMessage(messageElement) {
    let previousMessage = messageElement?.previousElementSibling ?? null;

    while (previousMessage) {
      if (
        previousMessage.matches?.('chat-message') &&
        previousMessage.getAttribute('role') === 'user'
      ) {
        return previousMessage;
      }
      previousMessage = previousMessage.previousElementSibling ?? null;
    }

    return null;
  }

  function sendChatEditRequest(messageId, content, { playSound = true } = {}) {
    const cleanContent = content.trim();
    if (!messageId || !cleanContent) {
      return;
    }

    pendingEditRequest = null;
    pendingKidcoreStreamingFx = cleanContent.toLowerCase().includes('glue shimmer') ? 'glue-shimmer' : null;
    if (playSound) {
      playKidcoreSend();
    }
    disableInput();
    wsClient.sendChatEdit(messageId, cleanContent);
  }

  function sendPendingChatRequest() {
    if (!pendingChatSendRequest) {
      return;
    }

    const { content } = pendingChatSendRequest;
    pendingChatSendRequest = null;
    pendingKidcoreStreamingFx = content.toLowerCase().includes('glue shimmer') ? 'glue-shimmer' : null;
    wsClient.sendChat(content);
  }

  setComposerState('idle');
  refreshEditableMessageState();

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
        setMessageState(currentAssistantMessage, 'streaming');
        applyGlueShimmerEffect(currentAssistantMessage);
        disableInput();
        showStreaming();
        scrollToBottom();
        break;

      case 'reasoning.start':
        // Signal to create a new reasoning block (for multiple reasoning segments)
        if (currentAssistantMessage) {
          currentAssistantMessage.startNewReasoningBlock();
        }
        break;

      case 'reasoning.chunk':
        if (currentAssistantMessage && msg.payload && msg.payload.content) {
          currentAssistantMessage.appendReasoning(msg.payload.content);
          playKidcoreChunk();
          pulseGlueShimmer(currentAssistantMessage);
          scrollToBottomIfNearBottom();
        }
        break;

      case 'chat.chunk':
        if (currentAssistantMessage && msg.payload && msg.payload.content) {
          currentAssistantMessage.appendContent(msg.payload.content);
          playKidcoreChunk();
          pulseGlueShimmer(currentAssistantMessage);
          scrollToBottomIfNearBottom();
        }
        break;

      case 'chat.complete':
        clearCurrentAssistantMessage();
        clearComposerEditState();
        playKidcoreMessageComplete();
        // Add copy buttons to any new code blocks
        addCopyButtons();
        if (pendingEditRequest) {
          const { messageId, content } = pendingEditRequest;
          sendChatEditRequest(messageId, content);
        } else if (pendingChatSendRequest) {
          sendPendingChatRequest();
        } else {
          enableInput();
          // Send next queued message if any
          processQueue();
        }
        break;

      case 'chat.cancelled':
        clearCurrentAssistantMessage({ remove: true });
        clearComposerEditState();
        scrollToBottom();
        if (pendingEditRequest) {
          const { messageId, content } = pendingEditRequest;
          sendChatEditRequest(messageId, content);
        } else if (pendingChatSendRequest) {
          sendPendingChatRequest();
        } else {
          enableInput();
          processQueue();
        }
        break;

      case 'chat.error':
        clearCurrentAssistantMessage();
        pendingEditRequest = null;
        pendingChatSendRequest = null;
        clearComposerEditState();
        playKidcoreError();
        showError(msg.payload?.error || 'An error occurred');
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

      case 'debug.info':
        handleDebugInfo(msg.payload);
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
      setCurrentAssistantMessage: (msg) => { currentAssistantMessage = msg; },
      getCurrentAssistantMessageState: () => currentAssistantMessage?.getMessageState?.() || currentAssistantMessage?.getAttribute('data-message-state') || null,
      getComposerState: () => composerState,
      getEditingMessageId: () => editingMessageElement?.getAttribute('message-id') || null,
    };
  }

  // Session Handlers
  function handleSessionNew(payload) {
    // Clear message list and history for new session
    messageList.innerHTML = '';
    messageHistory.length = 0;
    historyIndex = -1;
    currentAssistantMessage = null;
    pendingEditRequest = null;
    pendingChatSendRequest = null;
    clearComposerEditState();
    activeToolCalls.clear();
    activeSessionId = payload.sessionId || null;
    showSystemMessage(`New session created: ${payload.sessionId}`);
    enableInput();
  }

  function handleSessionLoaded(payload) {
    pendingEditRequest = null;
    pendingChatSendRequest = null;
    clearComposerEditState();
    reconcileSessionLoaded(payload);

    showSystemMessage(`Session resumed: ${payload.sessionId}`);
    addCopyButtons();
    // Ensure clean UI state after loading session
    if (currentAssistantMessage?.classList.contains('streaming')) {
      disableInput();
    } else {
      enableInput();
    }
  }

  function handleSessionList(payload) {
    const sessions = payload.sessions || [];

    if (sessions.length === 0) {
      clearComposerEditState();
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
    clearComposerEditState();
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
    if (payload.summary) {
      content += `\nSummary: ${payload.summary}\n`;
    }

    clearComposerEditState();
    showSystemMessage(content);
    enableInput();
  }

  function handleContextInfo(payload) {
    // Create context viewer container
    const container = document.createElement('div');
    container.className = 'context-viewer-message';

    // Create the context viewer component
    const contextViewer = document.createElement('context-viewer');
    contextViewer.setAttribute('data-context', JSON.stringify(payload));

    // Listen for refresh events
    contextViewer.addEventListener('context-refresh', () => {
      wsClient.sendCommand('/context');
    });

    // Listen for toggle events
    contextViewer.addEventListener('context-toggle', (e) => {
      const { section, enabled } = e.detail;
      console.log(`Context section ${section} toggled: ${enabled}`);
    });

    // Listen for command events to send to server
    contextViewer.addEventListener('send-command', (e) => {
      const { command } = e.detail;
      if (command) {
        wsClient.sendCommand(command);
      }
    });

    container.appendChild(contextViewer);
    messageList.appendChild(container);

    scrollToBottom();
    clearComposerEditState();
    enableInput();
  }

  function handleDebugInfo(payload) {
    const debugPanel = document.getElementById('debug-panel');
    if (!debugPanel) {
      console.error('Debug panel not found');
      return;
    }

    // Gather DOM message info
    const domMessages = Array.from(messageList.querySelectorAll('chat-message')).map(msg => ({
      id: msg.getAttribute('message-id') || 'NO-ID',
      role: msg.getAttribute('role') || 'unknown',
      content_length: (typeof msg.getContent === 'function' 
        ? msg.getContent() 
        : msg.getAttribute('content') || '').length,
      is_streaming: msg.classList.contains('streaming')
    }));

    // Gather current assistant info
    const currentAssistant = currentAssistantMessage ? {
      id: currentAssistantMessage.getAttribute('message-id') || 'NONE',
      role: currentAssistantMessage.getAttribute('role') || 'NONE',
      streaming: currentAssistantMessage.classList.contains('streaming'),
      content_length: (typeof currentAssistantMessage.getContent === 'function' 
        ? currentAssistantMessage.getContent() 
        : currentAssistantMessage.getAttribute('content') || '').length
    } : null;

    // WebSocket snapshot
    const wsSnapshot = wsClient.getConnectionSnapshot ? wsClient.getConnectionSnapshot() : {};

    // Build debug data
    const debugData = {
      messages: payload.messages || [],
      session: payload.session || {},
      websocket: {
        isConnected: wsClient.isConnected,
        reconnect_attempts: wsClient.reconnectAttempts,
        message_queue_length: wsClient.messageQueue?.length || 0,
        active_connections: payload.websocket?.active_connections || 0,
        traffic_log: payload.websocket?.traffic_log || [],
        snapshot: wsSnapshot
      },
      daemon: payload.daemon || { available: false },
      dom: {
        chat_message_count: domMessages.length,
        has_current_assistant: !!currentAssistantMessage,
        composer_state: composerState,
        current_assistant: currentAssistant,
        messages: domMessages
      }
    };

    debugPanel.open(debugData);
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
    const cleanContent = content.trim();
    if (!cleanContent) {
      return;
    }

    // Note: Inline editing is now handled via 'message-edited' event from chat-message component
    // This function only handles sending new messages

    // Add to history
    addToHistory(cleanContent);
    playKidcoreSend();

    // Send via WebSocket - commands use command.execute, chat uses chat.send
    if (cleanContent.startsWith('/')) {
      pendingKidcoreStreamingFx = null;

      // Commands: show as system message, don't disable input
      const cmdMsg = document.createElement('chat-message');
      cmdMsg.setAttribute('role', 'system');
      cmdMsg.setAttribute('content', `Command: ${cleanContent}`);
      cmdMsg.setAttribute('timestamp', new Date().toISOString());
      messageList.appendChild(cmdMsg);
      scrollToBottom();

      wsClient.sendCommand(cleanContent);
      // Don't disable input - commands are instant
      return;
    }

    pendingKidcoreStreamingFx = cleanContent.toLowerCase().includes('glue shimmer') ? 'glue-shimmer' : null;

    const userMessage = document.createElement('chat-message');
    userMessage.setAttribute('role', 'user');
    userMessage.setAttribute('content', cleanContent);
    userMessage.setAttribute('timestamp', new Date().toISOString());
    userMessage.setAttribute('message-id', createClientMessageId('user'));
    userMessage.setAttribute('data-session-message', 'true');
    messageList.appendChild(userMessage);

    if (currentAssistantMessage) {
      pendingChatSendRequest = { content: cleanContent };
      disableInput();
      scrollToBottom();
      handleStopGenerating();
      return;
    }

    disableInput();
    scrollToBottom();
    wsClient.sendChat(cleanContent);
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
    const retryRequest = getRetryRequest(messageElement);
    if (!retryRequest) {
      showError('Could not find the previous user prompt to regenerate this reply.');
      return;
    }

    // Remove the assistant message being regenerated from the DOM
    // so the new response replaces it instead of appending
    if (messageElement && messageElement.parentNode) {
      messageElement.remove();
    }
    // Clear reference if this was the current assistant message
    if (currentAssistantMessage === messageElement) {
      currentAssistantMessage = null;
    }

    if (currentAssistantMessage) {
      pendingEditRequest = retryRequest;
      handleStopGenerating();
      return;
    }

    sendChatEditRequest(retryRequest.messageId, retryRequest.content);
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
    messageInput.disabled = false;
    sendButton.disabled = false;
    if (stopButton) {
      stopButton.disabled = false;
      stopButton.hidden = false;
    }
    setComposerState('streaming');
    refreshEditableMessageState();
  }

  function setCancellingState() {
    if (stopButton) {
      stopButton.disabled = true;
      stopButton.style.opacity = '0.6';
    }
    setComposerState('cancelling');
  }

  function handleStopGenerating() {
    if (composerState === 'cancelling') {
      return;
    }

    // Even if currentAssistantMessage is null, we should still send cancel
    // and reset state to handle edge cases where UI is out of sync
    if (!currentAssistantMessage) {
      // Reset to idle state since there's no message to cancel
      enableInput();
      return;
    }

    setCancellingState();
    wsClient.sendCancel();
  }

  function enableInput() {
    messageInput.disabled = false;
    sendButton.disabled = false;
    if (stopButton) {
      stopButton.hidden = true;
      stopButton.disabled = false;
      stopButton.style.opacity = '';
    }
    setComposerState('idle');
    refreshEditableMessageState();
    messageInput.focus();
  }

  function scrollToBottom() {
    chatContainer.scrollTop = chatContainer.scrollHeight;
  }

  function scrollToBottomIfNearBottom() {
    // Only scroll if user is already near the bottom (within 400px)
    // This prevents auto-scroll from jumping while user is reading earlier content
    // 400px = ~3-4 lines of text, comfortable "eyeshot" of the bottom
    const scrollBottom = chatContainer.scrollTop + chatContainer.clientHeight;
    const isNearBottom = chatContainer.scrollHeight - scrollBottom < 400;
    if (isNearBottom) {
      chatContainer.scrollTop = chatContainer.scrollHeight;
    }
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
  stopButton?.addEventListener('click', handleStopGenerating);

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

    // Shift+Enter: Queue message if streaming, otherwise send immediately
    if (e.key === 'Enter' && e.shiftKey && composerState !== 'editing') {
      e.preventDefault();
      const content = messageInput.value.trim();
      if (content) {
        if (currentAssistantMessage) {
          addToQueue(content);
        } else {
          sendMessageContent(content);
        }
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

    if (e.key === 'Escape' && currentAssistantMessage && composerState !== 'cancelling') {
      e.preventDefault();
      handleStopGenerating();
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

    // Escape: cancel active response or clear queued messages
    if (e.key === 'Escape' && currentAssistantMessage && composerState !== 'cancelling') {
      e.preventDefault();
      handleStopGenerating();
      return;
    }

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

  messageList.addEventListener('edit-message', (event) => {
    // Inline editing is now handled within chat-message component
    // This event is kept for backward compatibility
    const messageElement = event.target?.closest?.('chat-message');
    if (!messageElement || messageElement.getAttribute('role') !== 'user') {
      return;
    }
    // Inline editing starts automatically when the edit button is clicked
    // No need to populate composer anymore
  });

  // Handle inline edit save
  messageList.addEventListener('message-edited', (event) => {
    const { messageId, newContent } = event.detail;
    const messageElement = event.target?.closest?.('chat-message');
    if (!messageElement || !messageId || !newContent) {
      return;
    }

    // Update the message content in the UI
    messageElement.setContent(newContent);

    // Remove messages after this one
    removeSessionMessagesAfter(messageElement);

    // Update history
    if (messageHistory.length === 0) {
      addToHistory(newContent);
    } else {
      messageHistory[messageHistory.length - 1] = newContent;
      historyIndex = messageHistory.length;
    }

    // Send the edit request to the backend
    pendingKidcoreStreamingFx = newContent.toLowerCase().includes('glue shimmer') ? 'glue-shimmer' : null;
    scrollToBottom();
    sendChatEditRequest(messageId, newContent, { playSound: false });
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

  // Mobile Chrome Hide/Show
  // Only header hides on scroll - footer (composer) stays visible
  const MOBILE_BREAKPOINT = 768;
  let isHeaderHidden = false;
  let lastScrollTop = chatContainer?.scrollTop || 0;
  let scrollDirection = 'none';
  let scrollDistance = 0;
  let scrollTimeout = null;

  // Guard states for top/bottom bounce handling
  let hasTopLeft = false;     // Must scroll down from top before header can hide
  let hasBottomLeft = false;  // Must scroll up from bottom before header can show (when hidden)
  let scrollHandlerInitialized = false;  // First scroll event just initializes state

  function getScrollInfo() {
    const scrollTop = chatContainer.scrollTop;
    const scrollHeight = chatContainer.scrollHeight;
    const clientHeight = chatContainer.clientHeight;
    const maxScroll = Math.max(0, scrollHeight - clientHeight);
    const distanceFromBottom = maxScroll - scrollTop;
    // Dynamic thresholds based on viewport size
    const minThreshold = Math.min(30, clientHeight * 0.05); // At least 5% of viewport or 30px
    const hideThreshold = Math.max(minThreshold, clientHeight * 0.08); // 8% to hide
    const showThreshold = Math.max(minThreshold * 0.5, clientHeight * 0.04); // 4% to show
    const edgeTolerance = Math.min(80, clientHeight * 0.12); // 12% tolerance for top/bottom
    return { scrollTop, maxScroll, distanceFromBottom, hideThreshold, showThreshold, edgeTolerance, clientHeight };
  }

  function handleScroll() {
    // Only apply on mobile
    if (window.innerWidth > MOBILE_BREAKPOINT) {
      if (isHeaderHidden) {
        showHeader();
      }
      return;
    }

    const { scrollTop, maxScroll, distanceFromBottom, hideThreshold, showThreshold, edgeTolerance } = getScrollInfo();
    
    // Always reset lastScrollTop on first real scroll to prevent jumpiness
    if (!scrollHandlerInitialized) {
      lastScrollTop = scrollTop;
      scrollHandlerInitialized = true;
      return;
    }

    // If chat area is too small to scroll meaningfully, don't hide header
    if (maxScroll < hideThreshold) {
      if (isHeaderHidden) {
        showHeader();
      }
      return;
    }

    const delta = scrollTop - lastScrollTop;
    lastScrollTop = scrollTop;

    // Update guard states based on position
    // At top: reset hasTopLeft, allow hasBottomLeft
    if (scrollTop <= edgeTolerance) {
      hasTopLeft = false;
      hasBottomLeft = true; // Can always show header when near top
    }
    // Past top tolerance: can now hide header
    else if (scrollTop > edgeTolerance) {
      hasTopLeft = true;
    }

    // At bottom: reset hasBottomLeft, keep hasTopLeft
    if (distanceFromBottom <= edgeTolerance) {
      hasBottomLeft = false;
      hasTopLeft = true; // Can always hide header when past top
    }
    // Past bottom tolerance: can now show header (if it was hidden)
    else if (distanceFromBottom > edgeTolerance) {
      hasBottomLeft = true;
    }

    // Clear any pending timeout
    if (scrollTimeout) {
      clearTimeout(scrollTimeout);
    }

    // Detect direction
    const newDirection = delta > 0 ? 'down' : 'up';

    // Reset distance on direction change
    if (newDirection !== scrollDirection) {
      scrollDirection = newDirection;
      scrollDistance = 0;
    }

    // Accumulate distance in current direction
    scrollDistance += Math.abs(delta);

    // Handle scroll down - hide header after threshold (only if we've left the top)
    if (scrollDirection === 'down' && !isHeaderHidden && hasTopLeft) {
      if (scrollDistance > hideThreshold) {
        hideHeader();
        scrollDistance = 0;
      }
    }

    // Handle scroll up - show header after threshold (only if we've left the bottom)
    if (scrollDirection === 'up' && isHeaderHidden && hasBottomLeft) {
      if (scrollDistance > showThreshold) {
        showHeader();
        scrollDistance = 0;
      }
    }

    // Reset scroll tracking after inactivity
    scrollTimeout = setTimeout(() => {
      scrollDirection = 'none';
      scrollDistance = 0;
    }, 200);
  }

  function hideHeader() {
    const header = document.querySelector('.app-header');
    if (header) {
      header.classList.add('hidden');
    }
    isHeaderHidden = true;
  }

  function showHeader() {
    const header = document.querySelector('.app-header');
    if (header) {
      header.classList.remove('hidden');
    }
    isHeaderHidden = false;
  }

  // Attach scroll listener
  chatContainer.addEventListener('scroll', handleScroll, { passive: true });

  // Restore header when focusing the composer
  messageInput.addEventListener('focus', () => {
    if (isHeaderHidden && window.innerWidth <= MOBILE_BREAKPOINT) {
      showHeader();
    }
    restoreChrome();
  });

  // Handle scroll for mobile chrome collapse
  window.addEventListener('scroll', handleScroll);

  // Handle window resize to reset hidden state on desktop
  window.addEventListener('resize', () => {
    if (window.innerWidth > MOBILE_BREAKPOINT && isHeaderHidden) {
      showHeader();
    }
    scrollToBottom();
  });

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

  // Floating settings button (mobile) - triggers the settings-menu
  const floatingSettingsBtn = document.getElementById('floating-settings-btn');
  if (floatingSettingsBtn) {
    // Show floating button on mobile (remove hidden attribute)
    if (window.innerWidth <= 768) {
      floatingSettingsBtn.removeAttribute('hidden');
    }

    // Update visibility on resize
    window.addEventListener('resize', () => {
      if (window.innerWidth <= 768) {
        floatingSettingsBtn.removeAttribute('hidden');
      } else {
        floatingSettingsBtn.setAttribute('hidden', '');
      }
    });

    // Click handler - open settings menu
    floatingSettingsBtn.addEventListener('click', (event) => {
      event.stopPropagation();
      const settingsMenu = document.querySelector('settings-menu');
      if (settingsMenu) {
        // Toggle settings menu by clicking its toggle button
        const toggleBtn = settingsMenu.querySelector('.settings-toggle');
        if (toggleBtn) {
          toggleBtn.click();
        }
      }
    });
  }
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

// ============================================
// Command Palette Initialization (PRD #159)
// ============================================

function initCommandPalette() {
  // Only initialize if the library is loaded
  if (typeof window.CommandPaletteLib === 'undefined') {
    console.warn('CommandPaletteLib not loaded, skipping palette initialization');
    return;
  }

  const { CommandPalette, CommandRegistry } = window.CommandPaletteLib;

  // Create palette instance
  const palette = new CommandPalette({
    placeholder: 'Type a command...'
  });

  // Register default commands
  CommandRegistry.register({
    id: 'clear-chat',
    title: 'Clear Chat',
    keywords: ['reset', 'clean', 'delete'],
    shortcut: 'Ctrl+Shift+C',
    action: () => {
      if (confirm('Clear all messages?')) {
        const messageList = document.getElementById('message-list');
        if (messageList) {
          messageList.innerHTML = '';
          window.addSystemMessage?.('Chat cleared');
        }
      }
    }
  });

  CommandRegistry.register({
    id: 'toggle-theme',
    title: 'Toggle Theme',
    keywords: ['dark', 'light', 'mode', 'color'],
    shortcut: 'Ctrl+Shift+T',
    action: () => {
      const currentTheme = document.documentElement.getAttribute('data-theme');
      const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', newTheme);
      localStorage.setItem('theme', newTheme);
      window.addSystemMessage?.(`Theme changed to ${newTheme}`);
    }
  });

  CommandRegistry.register({
    id: 'new-session',
    title: 'New Session',
    keywords: ['create', 'start', 'reset'],
    action: () => {
      if (confirm('Start a new session? Current conversation will be archived.')) {
        window.location.reload();
      }
    }
  });

  CommandRegistry.register({
    id: 'focus-input',
    title: 'Focus Input',
    keywords: ['type', 'write', 'compose'],
    shortcut: '/',
    action: () => {
      const input = document.getElementById('message-input');
      if (input) {
        input.focus();
      }
    }
  });

  console.log('Command palette initialized with', CommandRegistry.getAll().length, 'commands');

  // Store palette instance globally for debugging
  window.alfredCommandPalette = palette;
}

// ============================================
// Keyboard Shortcuts Initialization (PRD #159)
// ============================================

function initKeyboardShortcuts() {
  // Only initialize if the library is loaded
  if (typeof window.ShortcutRegistry === 'undefined' ||
      typeof window.KeyboardManager === 'undefined' ||
      typeof window.HelpModal === 'undefined' ||
      typeof window.MessageNavigator === 'undefined') {
    console.warn('Keyboard libraries not loaded, skipping keyboard shortcuts initialization');
    return;
  }

  const { ShortcutRegistry, KeyboardManager, HelpModal, MessageNavigator } = window;

  // Create help modal
  const helpModal = new HelpModal();

  // Create message navigator
  const messageNavigator = new MessageNavigator();

  // Create keyboard manager
  const keyboardManager = new KeyboardManager();

  // Register default shortcuts

  // Global shortcuts
  ShortcutRegistry.register({
    id: 'show-help',
    key: '?',
    description: 'Show keyboard shortcuts',
    category: 'Global',
    action: () => helpModal.toggle()
  });

  ShortcutRegistry.register({
    id: 'toggle-help',
    key: 'Shift+/',
    description: 'Show keyboard shortcuts',
    category: 'Global',
    action: () => helpModal.toggle()
  });

  // Navigation shortcuts
  ShortcutRegistry.register({
    id: 'focus-previous-message',
    key: 'ArrowUp',
    description: 'Previous message',
    category: 'Navigation',
    context: 'message-focused',
    action: () => messageNavigator.previous()
  });

  ShortcutRegistry.register({
    id: 'focus-next-message',
    key: 'ArrowDown',
    description: 'Next message',
    category: 'Navigation',
    context: 'message-focused',
    action: () => messageNavigator.next()
  });

  ShortcutRegistry.register({
    id: 'focus-first-message',
    key: 'Home',
    description: 'First message',
    category: 'Navigation',
    context: 'message-focused',
    action: () => messageNavigator.first()
  });

  ShortcutRegistry.register({
    id: 'focus-last-message',
    key: 'End',
    description: 'Last message',
    category: 'Navigation',
    context: 'message-focused',
    action: () => messageNavigator.last()
  });

  // Make messages focusable when they're added
  const makeMessagesFocusable = () => {
    messageNavigator.makeMessagesFocusable();
  };

  // Run initially and after new messages
  makeMessagesFocusable();

  // Watch for new messages
  const messageList = document.getElementById('message-list');
  if (messageList) {
    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
          makeMessagesFocusable();
        }
      }
    });
    observer.observe(messageList, { childList: true });
  }

  console.log('Keyboard shortcuts initialized with', ShortcutRegistry.getAllFlat().length, 'shortcuts');

  // Store instances globally for debugging
  window.alfredKeyboardManager = keyboardManager;
  window.alfredHelpModal = helpModal;
  window.alfredMessageNavigator = messageNavigator;
}

// ============================================
// Initialization
// ============================================

function initAll() {
  initAlfredUI();
  initCommandPalette();
  initKeyboardShortcuts();
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initAll);
} else {
  initAll();
}
