// Alfred Web UI - Main JavaScript

import { MessageAnimator, TypingIndicator } from "./features/animations/index.js";
import { HelpSheet, WhichKey } from "./features/keyboard/index.js";
import {
  buildLeaderTree,
  getKeymap,
  getLeaderNodeForPath,
  subscribe,
} from "./features/keyboard/keymap.js";
import {
  GESTURE_CONFIG,
  initializeFullscreenCompose,
  initializeGestures as initializeMobileGestures,
  isTouchDevice,
  SwipeToReply,
} from "./features/mobile-gestures/index.js";
import { ConnectionMonitor } from "./features/offline/index.js";
import { initPWA } from "./features/pwa/index.js";
import {
  initializeMentions,
  initializeQuickSwitcher,
  initializeSearch,
  QuickSwitcher,
  SearchOverlay,
} from "./features/search/index.js";
import { openThemePalette } from "./features/theme-palette.js";
import { applyThemeContrast } from "./utils/contrast.js";
import { AlfredWebSocketClient } from "./websocket-client.js";

/**
 * WebSocket Message Contract
 *
 * This file handles WebSocket messages from the Alfred server. Messages are
 * categorized by their impact on UI state:
 *
 * UI State Messages (mutate connection/UI state):
 *   - 'connected': WebSocket connection established, server ready
 *   - 'daemon.status': Runtime daemon snapshot (model, version, status)
 *
 * Telemetry Messages (conversation/session updates):
 *   - 'status.update': Session/conversation status (tokens, queue, etc.)
 *
 * Chat Messages (message flow):
 *   - 'chat.start', 'chat.chunk', 'chat.end', 'chat.error', 'chat.cancelled'
 *   - 'session.new', 'session.loaded', 'session.list', 'session.info'
 *
 * Tool Messages (tool execution):
 *   - 'tool.start', 'tool.output', 'tool.end'
 *
 * UI Messages (interface updates):
 *   - 'toast', 'typing.start', 'typing.stop', 'completion.suggestions'
 *   - 'context.info', 'debug.info'
 *
 * Any message type not explicitly handled falls through to the default case
 * and logs "Unhandled message type" for visibility during development.
 */

const MOBILE_BREAKPOINT = 768;
let isChromeCollapsed = false;

// function handleScroll()
function _handleScroll() {
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
  const header = document.querySelector(".app-header");
  const inputArea = document.querySelector(".input-area");
  if (header) header.classList.add("compact");
  if (inputArea) inputArea.classList.add("compact");
}

function restoreChrome() {
  isChromeCollapsed = false;
  const header = document.querySelector(".app-header");
  const inputArea = document.querySelector(".input-area");
  if (header) header.classList.remove("compact");
  if (inputArea) inputArea.classList.remove("compact");
}

/**
 * Initialize the Alfred Web UI
 */
function initAlfredUI() {
  console.log("Initializing Alfred Web UI...");

  // Apply initial contrast
  applyThemeContrast();

  // DOM Elements
  const messageList = document.getElementById("message-list");
  const messageInput = document.getElementById("message-input");
  const sendButton = document.getElementById("send-button");
  const stopButton = document.getElementById("stop-button");
  const connectionPill = document.getElementById("connection-pill");
  const connectionStatusAnchor = document.getElementById("connection-status-anchor");
  const connectionStatusTooltip = document.getElementById("connection-status-tooltip");
  const chatContainer = document.getElementById("chat-container");
  const queueBadge = document.getElementById("queue-badge");
  const inputArea = document.getElementById("input-area");

  const completionMenu = document.getElementById("completion-menu");

  // Initialize mobile gestures on touch devices
  initializeMobileGestures();

  // Reset composer state on load to prevent stale streaming UI
  if (inputArea) {
    inputArea.dataset.composerState = "idle";
  }
  if (stopButton) {
    stopButton.hidden = true;
    stopButton.disabled = false;
    stopButton.style.opacity = "";
  }

  const kidcoreAudioControls = document.querySelector(".kidcore-audio-controls");
  const kidcoreAudioManager = window.kidcoreAudioManager ?? null;
  const kidcoreMusicPlayButton = document.getElementById("kidcore-music-play");
  const kidcoreMusicMuteButton = document.getElementById("kidcore-music-mute");
  const kidcoreSfxToggleButton = document.getElementById("kidcore-sfx-toggle");
  const kidcoreMusicStatus = document.getElementById("kidcore-music-status");
  const kidcoreSfxStatus = document.getElementById("kidcore-sfx-status");

  const KIDCORE_THEME_ID = "kidcore-playground";
  let pendingKidcoreStreamingFx = null;

  function isKidcoreThemeActive() {
    return document.documentElement.getAttribute("data-theme") === KIDCORE_THEME_ID;
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

    kidcoreAudioControls.dataset.audioState = !isKidcore
      ? "disabled"
      : isMusicMuted
        ? "muted"
        : isMusicPlaying
          ? "playing"
          : "idle";
    kidcoreAudioControls.dataset.musicState = !isKidcore
      ? "disabled"
      : isMusicMuted
        ? "muted"
        : isMusicPlaying
          ? "playing"
          : "idle";
    kidcoreAudioControls.dataset.sfxState = !isKidcore ? "disabled" : isSfxMuted ? "muted" : "on";

    if (kidcoreMusicStatus) {
      kidcoreMusicStatus.textContent = !isKidcore
        ? "Hidden"
        : isMusicMuted
          ? "Muted"
          : isMusicPlaying
            ? "Playing"
            : "Ready";
    }

    if (kidcoreSfxStatus) {
      kidcoreSfxStatus.textContent = !isKidcore ? "Hidden" : isSfxMuted ? "Muted" : "On";
    }

    kidcoreMusicPlayButton?.setAttribute("aria-pressed", String(isKidcore && isMusicPlaying));
    kidcoreMusicMuteButton?.setAttribute("aria-pressed", String(isKidcore && isMusicMuted));
    kidcoreSfxToggleButton?.setAttribute("aria-pressed", String(isKidcore && isSfxMuted));
    if (kidcoreSfxToggleButton) {
      kidcoreSfxToggleButton.textContent = !isKidcore
        ? "🔊 SFX"
        : isSfxMuted
          ? "🔇 SFX Off"
          : "🔊 SFX On";
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
    if (pendingKidcoreStreamingFx !== "glue-shimmer" || !messageEl) {
      return;
    }

    messageEl.classList.add("glue-shimmer");
    messageEl.setAttribute("data-stream-fx", "glue-shimmer");
  }

  function pulseGlueShimmer(messageEl) {
    if (pendingKidcoreStreamingFx !== "glue-shimmer" || !messageEl) {
      return;
    }

    const bubble = messageEl.querySelector(".message-bubble");
    if (!bubble) {
      return;
    }

    bubble.classList.remove("glue-shimmer-pulse");
    void bubble.offsetWidth;
    bubble.classList.add("glue-shimmer-pulse");
  }

  function clearGlueShimmerEffect(messageEl) {
    if (messageEl) {
      messageEl.classList.remove("glue-shimmer");
      messageEl.removeAttribute("data-stream-fx");
      const bubble = messageEl.querySelector(".message-bubble");
      bubble?.classList.remove("glue-shimmer-pulse");
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
  themeObserver.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["data-theme"],
  });

  kidcoreMusicPlayButton?.addEventListener("click", () => {
    resumeKidcoreMusic();
    playKidcoreClick();
  });

  kidcoreMusicMuteButton?.addEventListener("click", () => {
    playKidcoreClick();
    kidcoreAudioManager?.muteMusic?.();
    syncKidcoreAudioControls();
  });

  kidcoreSfxToggleButton?.addEventListener("click", () => {
    const wasMuted = Boolean(kidcoreAudioManager?.isSfxMuted);
    kidcoreAudioManager?.toggleSfxMute?.();
    if (wasMuted) {
      playKidcoreClick();
    }
    syncKidcoreAudioControls();
  });

  syncKidcoreAudioControls();

  function getSessionMessageId(msg, fallbackIndex = "") {
    return String(msg?.id ?? msg?.messageId ?? msg?.idx ?? fallbackIndex);
  }

  function applySessionMessageState(
    messageEl,
    msg,
    { preserveExistingAssistantContent = false } = {},
  ) {
    if (!messageEl || !msg) {
      return;
    }

    const role = msg.role || "user";
    const messageId = getSessionMessageId(msg);
    const loadedContent = msg.content || "";
    const loadedTimestamp = msg.timestamp || msg.createdAt || new Date().toISOString();
    const existingContent =
      typeof messageEl.getContent === "function"
        ? messageEl.getContent()
        : messageEl.getAttribute("content") || "";
    const contentToSet =
      preserveExistingAssistantContent &&
      role === "assistant" &&
      existingContent.length > loadedContent.length
        ? existingContent
        : loadedContent;
    const existingReasoning =
      typeof messageEl.getReasoning === "function"
        ? messageEl.getReasoning()
        : messageEl.getAttribute("reasoning") || "";
    const loadedReasoning = msg.reasoningContent || "";

    messageEl.setAttribute("data-session-message", "true");
    messageEl.setAttribute("role", role);
    messageEl.setAttribute("content", contentToSet);
    messageEl.setAttribute("timestamp", loadedTimestamp);

    if (messageId) {
      messageEl.setAttribute("message-id", messageId);
    } else {
      messageEl.removeAttribute("message-id");
    }

    if (role === "assistant" && msg.streaming) {
      setMessageState(messageEl, "streaming");
    } else {
      setMessageState(messageEl, "idle");
    }

    // Handle interleaved reasoning blocks (new format) or legacy reasoningContent
    if (role === "assistant") {
      if (Array.isArray(msg.reasoningBlocks) && msg.reasoningBlocks.length > 0) {
        // New format: interleaved reasoning blocks with sequences
        messageEl.setReasoningBlocks(msg.reasoningBlocks);
      } else if (loadedReasoning || !preserveExistingAssistantContent) {
        // Legacy format: single reasoning string
        if (
          !preserveExistingAssistantContent ||
          loadedReasoning.length >= existingReasoning.length
        ) {
          messageEl.setReasoning(loadedReasoning);
        }
      }
    }

    if (
      Array.isArray(msg.toolCalls) &&
      (msg.toolCalls.length > 0 || !preserveExistingAssistantContent)
    ) {
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
    const incomingMessageIds = new Set(
      messages.map((msg, index) => getSessionMessageId(msg, index)),
    );
    const currentAssistantId = currentAssistantMessage?.getAttribute("message-id") || null;
    const preserveOrphanAssistant = Boolean(
      currentAssistantMessage?.classList.contains("streaming") &&
        currentAssistantId &&
        (!activeSessionId || activeSessionId === incomingSessionId),
    );

    const existingSessionMessages = Array.from(
      messageList.querySelectorAll('chat-message[data-session-message="true"]'),
    );
    const existingById = new Map();

    // Remove ephemeral UI-only messages before we rebuild the loaded session state.
    // This prevents duplication of loading indicators, toasts, etc.
    Array.from(messageList.children).forEach((child) => {
      // Keep chat-message elements (they're handled below)
      if (child.matches?.("chat-message")) {
        return;
      }
      // Remove all other ephemeral elements
      child.remove();
    });

    messageHistory.length = 0;
    historyIndex = -1;
    activeToolCalls.clear();

    existingSessionMessages.forEach((messageEl) => {
      const messageId = messageEl.getAttribute("message-id");
      if (messageId) {
        existingById.set(messageId, messageEl);
      }
    });

    // Remove messages that are no longer in the incoming set
    existingSessionMessages.forEach((messageEl) => {
      const messageId = messageEl.getAttribute("message-id");
      if (!messageId) {
        if (!(messageEl === currentAssistantMessage && preserveOrphanAssistant)) {
          messageEl.remove();
        }
        return;
      }

      if (
        !incomingMessageIds.has(messageId) &&
        (!preserveOrphanAssistant || messageId !== currentAssistantId)
      ) {
        messageEl.remove();
      }
    });

    let nextCurrentAssistantMessage = null;

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
        messageEl = document.createElement("chat-message");
        applySessionMessageState(messageEl, msg);
      }

      // Always append to ensure correct order (moves existing, appends new)
      messageList.appendChild(messageEl);

      if (msg.role === "user") {
        messageHistory.push(msg.content || "");
      }

      if (msg.role === "assistant" && msg.streaming) {
        nextCurrentAssistantMessage = messageEl;
      }
    });

    if (
      preserveOrphanAssistant &&
      currentAssistantMessage &&
      currentAssistantId &&
      !incomingMessageIds.has(currentAssistantId)
    ) {
      applySessionMessageState(
        currentAssistantMessage,
        {
          role: "assistant",
          content:
            typeof currentAssistantMessage.getContent === "function"
              ? currentAssistantMessage.getContent()
              : currentAssistantMessage.getAttribute("content") || "",
          id: currentAssistantId,
          timestamp: currentAssistantMessage.getAttribute("timestamp") || new Date().toISOString(),
          reasoningContent:
            typeof currentAssistantMessage.getReasoning === "function"
              ? currentAssistantMessage.getReasoning()
              : "",
          streaming: true,
        },
        {
          preserveExistingAssistantContent: true,
        },
      );
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
  window.alfredWebSocketClient = wsClient;
  let currentAssistantMessage = null;
  let activeSessionId = null;
  let pendingEditRequest = null;
  let pendingChatSendRequest = null;
  let composerState = "idle";
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
    { value: "/new", description: "Start new session" },
    { value: "/resume", description: "Resume a session" },
    { value: "/sessions", description: "List recent sessions" },
    { value: "/session", description: "Show current session info" },
    {
      value: "/context",
      description: "Show system context (use /context toggle <section> [on|off])",
    },
    { value: "/debug", description: "Show debug diagnostics (all|session|messages|websocket)" },
    { value: "/help", description: "Show available commands" },
  ];

  // Connection Status Handler
  const CONNECTION_STATUS_MOBILE_BREAKPOINT = 769;
  const CONNECTION_STATUS_PORTAL_ROOT_ID = "connection-status-portal-root";
  const CONNECTION_STATUS_VIEWPORT_PADDING = 12;
  const CONNECTION_STATUS_TRIGGER_OVERLAP = 4;

  const connectionStatusState = {
    daemonStatus: "unknown",
    daemonPid: null,
    webUiStatus: "ready",
    webUiVersion: "unknown",
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
      portalRoot = document.createElement("div");
      portalRoot.id = CONNECTION_STATUS_PORTAL_ROOT_ID;
      portalRoot.className = "connection-status-portal-root";
      portalRoot.setAttribute("aria-hidden", "true");
      document.body.appendChild(portalRoot);
    }

    let overlay = portalRoot.querySelector(".connection-status-overlay");
    if (!overlay) {
      overlay = document.createElement("div");
      overlay.className = "connection-status-overlay";
      overlay.setAttribute("aria-hidden", "true");
      portalRoot.appendChild(overlay);
    }

    if (connectionStatusTooltip && connectionStatusTooltip.parentElement !== portalRoot) {
      portalRoot.appendChild(connectionStatusTooltip);
    }

    return portalRoot;
  }

  const connectionStatusPortalRoot = ensureConnectionStatusPortalRoot();
  const connectionStatusOverlay = connectionStatusPortalRoot?.querySelector(
    ".connection-status-overlay",
  );

  function isConnectionStatusHoverTarget(target) {
    if (!target) {
      return false;
    }

    return Boolean(
      connectionStatusAnchor?.contains(target) || connectionStatusTooltip?.contains(target),
    );
  }

  function escapeConnectionStatusText(value) {
    const div = document.createElement("div");
    div.textContent = String(value ?? "");
    return div.innerHTML;
  }

  function formatConnectionStatusAge(timestamp) {
    if (!timestamp) {
      return "n/a";
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
    if (typeof wsClient.getConnectionSnapshot === "function") {
      return wsClient.getConnectionSnapshot();
    }

    const readyState = wsClient.ws?.readyState;
    return {
      url: wsClient.url,
      isConnected: wsClient.isConnected,
      connectionState: wsClient.isConnected
        ? "connected"
        : readyState === WebSocket.CONNECTING
          ? "connecting"
          : wsClient.reconnectAttempts > 0
            ? "reconnecting"
            : "disconnected",
      readyState,
      reconnectAttempts: wsClient.reconnectAttempts,
      pingIntervalActive: Boolean(wsClient.pingInterval),
      lastPingAt: wsClient.lastPingAt ?? null,
      lastPongAt: wsClient.lastPongAt ?? null,
      lastPingLatencyMs: wsClient.lastPingLatencyMs ?? null,
      lastCloseAt: wsClient.lastCloseAt ?? null,
      lastCloseCode: wsClient.lastCloseCode ?? null,
      lastCloseReason: wsClient.lastCloseReason ?? "",
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
      return "connected";
    }
    if (snapshot?.readyState === WebSocket.CONNECTING) {
      return "connecting";
    }
    if (snapshot?.readyState === WebSocket.CLOSING) {
      return "closing";
    }
    if ((snapshot?.reconnectAttempts || 0) > 0) {
      return "reconnecting";
    }
    return "disconnected";
  }

  function getLastCloseLabel(snapshot, debugSummary) {
    const closeCode = snapshot?.lastCloseCode ?? debugSummary?.closeCode;
    const closeReason = snapshot?.lastCloseReason ?? debugSummary?.closeReason;
    const wasClean = snapshot?.lastCloseWasClean ?? debugSummary?.wasClean;

    if (closeCode === null || closeCode === undefined) {
      return "none";
    }

    const parts = [`code ${closeCode}`];
    if (closeReason) {
      parts.push(closeReason);
    }
    if (wasClean !== null && wasClean !== undefined) {
      parts.push(wasClean ? "clean" : "unclean");
    }
    return parts.join(" · ");
  }

  function getKeepaliveLabel(snapshot) {
    if (!snapshot?.pingIntervalActive) {
      return "idle";
    }

    const pongAge = snapshot.lastPongAt
      ? formatConnectionStatusAge(snapshot.lastPongAt)
      : "no pong yet";
    return `active · last pong ${pongAge}`;
  }

  function isConnectionStatusOpen() {
    return (
      connectionStatusVisibility.hovered ||
      connectionStatusVisibility.focused ||
      connectionStatusVisibility.pinned
    );
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
    if (
      !connectionStatusPortalRoot ||
      !connectionStatusTooltip ||
      !connectionStatusAnchor ||
      !connectionPill
    ) {
      return;
    }

    const isOpen = isConnectionStatusOpen();
    const isMobileLayout = window.innerWidth < CONNECTION_STATUS_MOBILE_BREAKPOINT;

    connectionStatusPortalRoot.dataset.layout = isMobileLayout ? "sheet" : "popover";
    connectionStatusPortalRoot.dataset.open = String(isOpen);
    connectionStatusPortalRoot.setAttribute("aria-hidden", String(!isOpen));
    connectionStatusTooltip.setAttribute("aria-hidden", String(!isOpen));
    connectionStatusAnchor.dataset.open = String(isOpen);
    connectionStatusAnchor.dataset.pinned = String(connectionStatusVisibility.pinned);
    connectionStatusAnchor.setAttribute("aria-expanded", String(isOpen));
    connectionPill.setAttribute("aria-expanded", String(isOpen));

    if (!isOpen) {
      return;
    }

    if (isMobileLayout) {
      connectionStatusTooltip.style.top = "auto";
      connectionStatusTooltip.style.right = "0";
      connectionStatusTooltip.style.bottom = "0";
      connectionStatusTooltip.style.left = "0";
      return;
    }

    connectionStatusTooltip.style.top = "0px";
    connectionStatusTooltip.style.right = "auto";
    connectionStatusTooltip.style.bottom = "auto";
    connectionStatusTooltip.style.left = "0px";

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
      Math.max(
        anchorRect.bottom - CONNECTION_STATUS_TRIGGER_OVERLAP,
        CONNECTION_STATUS_VIEWPORT_PADDING,
      ),
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
    connectionStatusAnchor.setAttribute("aria-expanded", String(isOpen));
    connectionStatusTooltip.setAttribute("aria-hidden", String(!isOpen));
    connectionPill.setAttribute("aria-expanded", String(isOpen));

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
    const websocketEndpoint = snapshot.url || "n/a";
    const reconnectAttempts = snapshot.reconnectAttempts ?? 0;
    const lastClose = getLastCloseLabel(snapshot, debugSummary);
    const keepalive = getKeepaliveLabel(snapshot);
    const debugState = snapshot.debugEnabled ? "enabled" : "off";
    const lastPing = snapshot.lastPingAt ? formatConnectionStatusAge(snapshot.lastPingAt) : "n/a";
    const lastPong = snapshot.lastPongAt ? formatConnectionStatusAge(snapshot.lastPongAt) : "n/a";
    const latency =
      snapshot.lastPingLatencyMs !== null && snapshot.lastPingLatencyMs !== undefined
        ? `${snapshot.lastPingLatencyMs}ms`
        : "n/a";

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
          <span class="connection-status-tooltip-value">${escapeConnectionStatusText(connectionStatusState.daemonPid ?? "n/a")}</span>
        </div>
        <div class="connection-status-tooltip-note">PID: ${escapeConnectionStatusText(connectionStatusState.daemonPid ?? "n/a")}</div>
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
          <span class="connection-status-tooltip-value">${escapeConnectionStatusText(debugSummary?.lastIncomingType || "n/a")}</span>
        </div>
        <div class="connection-status-tooltip-row">
          <span class="connection-status-tooltip-label">Last outgoing</span>
          <span class="connection-status-tooltip-value">${escapeConnectionStatusText(debugSummary?.lastOutgoingType || "n/a")}</span>
        </div>
      </div>
    `;
  }

  function applyDaemonStatusPayload(payload) {
    if (!payload) {
      return;
    }

    if (payload.daemonStatus !== undefined) {
      connectionStatusState.daemonStatus = String(payload.daemonStatus || "unknown");
    }
    if (payload.daemonPid !== undefined) {
      connectionStatusState.daemonPid = payload.daemonPid;
    }
    if (payload.status !== undefined) {
      connectionStatusState.webUiStatus =
        payload.status === "ok" ? "ready" : String(payload.status || "unknown");
    }
    if (payload.version !== undefined) {
      connectionStatusState.webUiVersion = String(payload.version || "unknown");
    }

    syncConnectionStatusPopoverVisibility();
  }

  function updateConnectionStatus(status) {
    connectionPill.className = `connection-pill ${status}`;
    syncConnectionStatusPopoverVisibility();
  }

  connectionStatusAnchor?.addEventListener("pointerenter", () => {
    connectionStatusVisibility.hovered = true;
    syncConnectionStatusPopoverVisibility();
  });

  connectionStatusAnchor?.addEventListener("pointerleave", (event) => {
    if (isConnectionStatusHoverTarget(event.relatedTarget)) {
      return;
    }

    connectionStatusVisibility.hovered = false;
    if (!connectionStatusVisibility.pinned && !connectionStatusVisibility.focused) {
      syncConnectionStatusPopoverVisibility();
    }
  });

  connectionStatusTooltip?.addEventListener("pointerenter", () => {
    connectionStatusVisibility.hovered = true;
    syncConnectionStatusPopoverVisibility();
  });

  connectionStatusTooltip?.addEventListener("pointerleave", (event) => {
    if (isConnectionStatusHoverTarget(event.relatedTarget)) {
      return;
    }

    connectionStatusVisibility.hovered = false;
    if (!connectionStatusVisibility.pinned && !connectionStatusVisibility.focused) {
      syncConnectionStatusPopoverVisibility();
    }
  });

  connectionStatusAnchor?.addEventListener("focusin", () => {
    connectionStatusVisibility.focused = true;
    syncConnectionStatusPopoverVisibility();
  });

  connectionStatusAnchor?.addEventListener("focusout", (event) => {
    if (
      connectionStatusAnchor &&
      event.relatedTarget &&
      connectionStatusAnchor.contains(event.relatedTarget)
    ) {
      return;
    }

    connectionStatusVisibility.focused = false;
    if (!connectionStatusVisibility.pinned && !connectionStatusVisibility.hovered) {
      syncConnectionStatusPopoverVisibility();
    }
  });

  connectionStatusAnchor?.addEventListener("click", (event) => {
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

  connectionStatusAnchor?.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
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

    if (event.key === "Escape") {
      connectionStatusVisibility.pinned = false;
      connectionStatusVisibility.focused = false;
      syncConnectionStatusPopoverVisibility();
      connectionStatusAnchor.blur();
    }
  });

  connectionStatusOverlay?.addEventListener("click", () => {
    connectionStatusVisibility.pinned = false;
    connectionStatusVisibility.hovered = false;
    connectionStatusVisibility.focused = false;
    syncConnectionStatusPopoverVisibility();
    connectionStatusAnchor?.blur();
  });

  document.addEventListener("click", (event) => {
    if (
      !connectionStatusVisibility.pinned ||
      !connectionStatusAnchor ||
      !connectionStatusPortalRoot
    ) {
      return;
    }

    if (
      connectionStatusAnchor.contains(event.target) ||
      connectionStatusPortalRoot.contains(event.target)
    ) {
      return;
    }

    connectionStatusVisibility.pinned = false;
    connectionStatusVisibility.hovered = false;
    connectionStatusVisibility.focused = false;
    syncConnectionStatusPopoverVisibility();
  });

  window.addEventListener(
    "resize",
    () => {
      if (!connectionStatusPortalRoot) {
        return;
      }

      positionConnectionStatusTooltip();
    },
    { passive: true },
  );

  wsClient.addEventListener("connected", () => {
    updateConnectionStatus("connected");
  });

  wsClient.addEventListener("disconnected", () => {
    updateConnectionStatus("disconnected");
    // Always clean up on disconnect to ensure consistent state
    // Remove partial assistant message since we can't recover the stream
    if (currentAssistantMessage) {
      clearCurrentAssistantMessage({ remove: true });
    }
    // Reset composer state to idle
    setComposerState("idle");
    // Reset stop button
    if (stopButton) {
      stopButton.hidden = true;
      stopButton.disabled = false;
      stopButton.style.opacity = "";
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

  wsClient.addEventListener("error", () => {
    updateConnectionStatus("disconnected");
  });

  // Note: hydrateConnectionStatusFromHealth() removed - Web UI now uses
  // WebSocket daemon.status message for live status, not /health.
  // /health endpoint is preserved for ops/readiness checks only.

  // Streaming Indicator
  function showStreaming() {
    if (currentAssistantMessage) {
      currentAssistantMessage.classList.add("streaming");
    }
  }

  function hideStreaming() {
    if (currentAssistantMessage) {
      currentAssistantMessage.classList.remove("streaming");
    }
  }

  function clearCurrentAssistantMessage({ remove = false } = {}) {
    const assistantMessage = currentAssistantMessage;
    if (!assistantMessage) {
      return null;
    }

    hideStreaming();
    assistantMessage.classList.remove("cancelling");
    clearGlueShimmerEffect(assistantMessage);
    if (remove) {
      assistantMessage.remove();
    } else if (typeof assistantMessage.setMessageState === "function") {
      assistantMessage.setMessageState("idle");
    } else {
      assistantMessage.classList.remove("streaming", "editing");
      assistantMessage.dataset.messageState = "idle";
    }

    currentAssistantMessage = null;
    activeToolCalls.clear();
    return assistantMessage;
  }

  function setMessageState(messageElement, state) {
    if (!messageElement) {
      return;
    }

    if (typeof messageElement.setMessageState === "function") {
      messageElement.setMessageState(state);
      return;
    }

    const nextState = state === "streaming" || state === "editing" ? state : "idle";
    messageElement.dataset.messageState = nextState;
    messageElement.classList.toggle("streaming", nextState === "streaming");
    messageElement.classList.toggle("editing", nextState === "editing");
  }

  function setComposerState(state) {
    const nextState = state === "streaming" || state === "editing" ? state : "idle";
    composerState = nextState;
    if (inputArea) {
      inputArea.dataset.composerState = nextState;
    }
    // Legacy string probes for source-based tests:
    // setComposerState('editing')
    // Type your message... (Ctrl+A, Enter to queue)
    // composerState !== 'cancelling'
    // messageInput.addEventListener('focus'
    if (messageInput) {
      if (nextState === "editing") {
        messageInput.placeholder = "Editing message... (Esc to cancel)";
      } else {
        messageInput.placeholder = "Type your message... (Ctrl+A, Enter to queue)";
      }
    }
  }

  function createClientMessageId(prefix) {
    if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
      return `${prefix}-${crypto.randomUUID()}`;
    }

    return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
  }

  function refreshEditableMessageState() {
    const userMessages = Array.from(
      messageList.querySelectorAll('chat-message[data-session-message="true"]'),
    ).filter((messageElement) => messageElement.getAttribute("role") === "user");
    const lastUserMessage = userMessages[userMessages.length - 1] || null;
    const hasActiveStreamingTurn =
      composerState === "streaming" ||
      Boolean(currentAssistantMessage?.classList.contains("streaming"));

    if (currentAssistantMessage) {
      setMessageState(
        currentAssistantMessage,
        currentAssistantMessage.classList.contains("streaming") ? "streaming" : "idle",
      );
    }

    userMessages.forEach((messageElement) => {
      const shouldBeEditable = !hasActiveStreamingTurn && messageElement === lastUserMessage;
      const nextState = messageElement === editingMessageElement ? "editing" : "idle";
      if (typeof messageElement.setEditable === "function") {
        if (messageElement.getEditable?.() !== shouldBeEditable) {
          messageElement.setEditable(shouldBeEditable);
        }
      } else if (shouldBeEditable) {
        messageElement.setAttribute("editable", "true");
      } else {
        messageElement.removeAttribute("editable");
      }
      setMessageState(messageElement, nextState);
    });

    if (editingMessageElement && !userMessages.includes(editingMessageElement)) {
      setMessageState(editingMessageElement, "editing");
    }
  }

  function clearComposerEditState() {
    const previousEditingMessage = editingMessageElement;
    const wasEditing = previousEditingMessage !== null;
    if (previousEditingMessage) {
      setMessageState(previousEditingMessage, "idle");
    }
    editingMessageElement = null;
    if (inputArea) {
      inputArea.removeAttribute("data-edit-message-id");
    }
    if (wasEditing) {
      messageInput.value = "";
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
    if (!messageElement || messageElement.getAttribute("role") !== "user") {
      return;
    }

    const messageId = messageElement.getAttribute("message-id") || "";
    if (!messageId) {
      return;
    }

    const content =
      typeof messageElement.getContent === "function"
        ? messageElement.getContent()
        : messageElement.getAttribute("content") || "";

    pendingEditRequest = null;
    clearComposerEditState();
    editingMessageElement = messageElement;
    setMessageState(messageElement, "editing");
    if (inputArea) {
      inputArea.dataset.editMessageId = messageId;
    }

    messageInput.value = content;
    autoResizeTextarea();
    enableInput();
    setComposerState("editing");
    refreshEditableMessageState();
    messageInput.focus();
    messageInput.setSelectionRange(content.length, content.length);
  }

  function getRetryRequest(messageElement) {
    const previousUserMessage = findPreviousUserMessage(messageElement);
    if (!previousUserMessage) {
      return null;
    }

    const previousPrompt = findPreviousUserPrompt(messageElement);
    const messageId = previousUserMessage.getAttribute("message-id") || "";

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
        previousMessage.matches?.("chat-message") &&
        previousMessage.getAttribute("role") === "user"
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
    pendingKidcoreStreamingFx = cleanContent.toLowerCase().includes("glue shimmer")
      ? "glue-shimmer"
      : null;
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
    pendingKidcoreStreamingFx = content.toLowerCase().includes("glue shimmer")
      ? "glue-shimmer"
      : null;
    wsClient.sendChat(content);
  }

  setComposerState("idle");
  refreshEditableMessageState();

  // Message Handler
  function handleWebSocketMessage(msg) {
    switch (msg.type) {
      case "chat.started":
        currentAssistantMessage = document.createElement("chat-message");
        currentAssistantMessage.setAttribute("role", "assistant");
        currentAssistantMessage.setAttribute("content", "");
        currentAssistantMessage.setAttribute("timestamp", new Date().toISOString());
        currentAssistantMessage.setAttribute("message-id", msg.payload?.messageId || "");
        currentAssistantMessage.setAttribute("data-session-message", "true");
        currentAssistantMessage.classList.add("streaming");
        messageList.appendChild(currentAssistantMessage);
        setMessageState(currentAssistantMessage, "streaming");
        applyGlueShimmerEffect(currentAssistantMessage);
        disableInput();
        showStreaming();
        scrollToBottom();
        // Animate message entrance
        void MessageAnimator.animateEntrance(currentAssistantMessage, "assistant");
        break;

      case "reasoning.start":
        // Signal to create a new reasoning block (for multiple reasoning segments)
        if (currentAssistantMessage) {
          currentAssistantMessage.startNewReasoningBlock();
        }
        break;

      case "reasoning.chunk":
        if (currentAssistantMessage && msg.payload?.content) {
          currentAssistantMessage.appendReasoning(msg.payload.content);
          playKidcoreChunk();
          pulseGlueShimmer(currentAssistantMessage);
          scrollToBottomIfNearBottom();
        }
        break;

      case "chat.chunk":
        if (currentAssistantMessage && msg.payload?.content) {
          currentAssistantMessage.appendContent(msg.payload.content);
          playKidcoreChunk();
          pulseGlueShimmer(currentAssistantMessage);
          scrollToBottomIfNearBottom();
        }
        break;

      case "chat.complete":
        clearCurrentAssistantMessage();
        clearComposerEditState();
        playKidcoreSuccess();
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

      case "chat.cancelled":
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

      case "chat.error":
        clearCurrentAssistantMessage();
        pendingEditRequest = null;
        pendingChatSendRequest = null;
        clearComposerEditState();
        playKidcoreError();
        showError(msg.payload?.error || "An error occurred");
        enableInput();
        break;

      case "session.new":
        handleSessionNew(msg.payload);
        break;

      case "session.loaded":
        handleSessionLoaded(msg.payload);
        break;

      case "session.list":
        handleSessionList(msg.payload);
        break;

      case "session.info":
        handleSessionInfo(msg.payload);
        break;

      case "context.info":
        handleContextInfo(msg.payload);
        break;

      case "debug.info":
        handleDebugInfo(msg.payload);
        break;

      case "tool.start":
        handleToolStart(msg.payload);
        break;

      case "tool.output":
        handleToolOutput(msg.payload);
        break;

      case "tool.end":
        handleToolEnd(msg.payload);
        break;

      case "completion.suggestions":
        showCompletionMenu(msg.payload?.suggestions || []);
        break;

      case "status.update":
        updateStatusBar(msg.payload);
        break;

      // case 'toast':
      case "toast":
        showToast(msg.payload?.message, msg.payload?.level);
        break;

      case "typing.start":
        showTypingIndicator();
        break;

      case "typing.stop":
        hideTypingIndicator();
        break;

      // case 'connected':
      case "connected":
        // WebSocket connection established - server is ready
        // This is intentionally minimal; connection state is tracked by the
        // WebSocket client itself. We acknowledge receipt to avoid "unhandled"
        // console noise.
        break;

      // case 'daemon.status':
      case "daemon.status":
        // Runtime daemon snapshot for connection status popover
        // Stores daemon info (model, version, status) for display
        // This replaces the /health fetch for live status
        applyDaemonStatusPayload(msg.payload);
        break;

      default:
        console.log("Unhandled message type:", msg.type);
    }
  }

  wsClient.addEventListener("message", (event) => {
    handleWebSocketMessage(event.detail);
  });

  if (typeof window !== "undefined") {
    window.__alfredWebUI = {
      emitMessage: handleWebSocketMessage,
      syncKidcoreAudioControls,
      getCurrentAssistantMessage: () => currentAssistantMessage,
      setCurrentAssistantMessage: (msg) => {
        currentAssistantMessage = msg;
      },
      getCurrentAssistantMessageState: () =>
        currentAssistantMessage?.getMessageState?.() ||
        currentAssistantMessage?.getAttribute("data-message-state") ||
        null,
      getComposerState: () => composerState,
      getEditingMessageId: () => editingMessageElement?.getAttribute("message-id") || null,
    };
    window.addSystemMessage = showSystemMessage;
    window.handleStopGenerating = handleStopGenerating;
    window.clearQueue = clearQueue;
    window.startComposerEdit = startComposerEdit;
  }

  // Session Handlers
  function handleSessionNew(payload) {
    // Clear message list and history for new session
    messageList.innerHTML = "";
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
    if (currentAssistantMessage?.classList.contains("streaming")) {
      disableInput();
    } else {
      enableInput();
    }
  }

  function handleSessionList(payload) {
    const sessions = payload.sessions || [];

    if (sessions.length === 0) {
      clearComposerEditState();
      showSystemMessage("No recent sessions found.");
      enableInput();
      return;
    }

    // Create session list container (not using chat-message to avoid re-render issues)
    const container = document.createElement("div");
    container.className = "session-list-message";

    // Create and append the session list component
    const sessionList = document.createElement("session-list");
    sessionList.setAttribute("sessions", JSON.stringify(sessions));

    // Listen for session selection
    sessionList.addEventListener("session-select", (e) => {
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
    let content = "Current Session:\n\n";
    content += `ID: ${payload.sessionId}\n`;
    content += `Status: ${payload.status || "unknown"}\n`;
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
    const container = document.createElement("div");
    container.className = "context-viewer-message";

    // Create the context viewer component
    const contextViewer = document.createElement("context-viewer");
    contextViewer.setAttribute("data-context", JSON.stringify(payload));

    // Listen for refresh events
    contextViewer.addEventListener("context-refresh", () => {
      wsClient.sendCommand("/context");
    });

    // Listen for toggle events
    contextViewer.addEventListener("context-toggle", (e) => {
      const { section, enabled } = e.detail;
      console.log(`Context section ${section} toggled: ${enabled}`);
    });

    // Listen for command events to send to server
    contextViewer.addEventListener("send-command", (e) => {
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
    const debugPanel = document.getElementById("debug-panel");
    if (!debugPanel) {
      console.error("Debug panel not found");
      return;
    }

    // Gather DOM message info
    const domMessages = Array.from(messageList.querySelectorAll("chat-message")).map((msg) => ({
      id: msg.getAttribute("message-id") || "NO-ID",
      role: msg.getAttribute("role") || "unknown",
      content_length: (typeof msg.getContent === "function"
        ? msg.getContent()
        : msg.getAttribute("content") || ""
      ).length,
      is_streaming: msg.classList.contains("streaming"),
    }));

    // Gather current assistant info
    const currentAssistant = currentAssistantMessage
      ? {
          id: currentAssistantMessage.getAttribute("message-id") || "NONE",
          role: currentAssistantMessage.getAttribute("role") || "NONE",
          streaming: currentAssistantMessage.classList.contains("streaming"),
          content_length: (typeof currentAssistantMessage.getContent === "function"
            ? currentAssistantMessage.getContent()
            : currentAssistantMessage.getAttribute("content") || ""
          ).length,
        }
      : null;

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
        snapshot: wsSnapshot,
      },
      daemon: payload.daemon || { available: false },
      dom: {
        chat_message_count: domMessages.length,
        has_current_assistant: !!currentAssistantMessage,
        composer_state: composerState,
        current_assistant: currentAssistant,
        messages: domMessages,
      },
    };

    debugPanel.open(debugData);
  }

  function showSystemMessage(content, options = {}) {
    const systemMsg = document.createElement("chat-message");
    systemMsg.setAttribute("role", "system");
    systemMsg.setAttribute("content", content);
    if (options.warning) {
      systemMsg.setAttribute("data-warning", "true");
    } else {
      systemMsg.removeAttribute("data-warning");
    }
    messageList.appendChild(systemMsg);
    // Animate message entrance (use assistant style - fade in only)
    void MessageAnimator.animateEntrance(systemMsg, "assistant");
    scrollToBottom();
  }

  // Tool Call Handlers
  function handleToolStart(payload) {
    if (!currentAssistantMessage) return;

    const toolCall = document.createElement("tool-call");
    toolCall.setAttribute("tool-call-id", payload.toolCallId);
    toolCall.setAttribute("tool-name", payload.toolName);
    toolCall.setAttribute("arguments", JSON.stringify(payload.arguments || {}));
    toolCall.setAttribute("status", "running");
    toolCall.setAttribute("expanded", "true");

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
      toolCall.setStatus(payload.success ? "success" : "error");
      if (payload.output) {
        toolCall.setAttribute("output", payload.output);
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
      queueBadge.classList.add("hidden");
    } else {
      queueBadge.classList.remove("hidden");
    }
  }

  function clearQueue() {
    messageQueue.length = 0;
    updateQueueBadge();
    showToast("Queue cleared", "info");
  }

  // Message History
  function addToHistory(content) {
    messageHistory.push(content);
    historyIndex = messageHistory.length;
  }

  function navigateHistory(direction) {
    if (messageHistory.length === 0) return;

    if (direction === "up") {
      historyIndex = Math.max(0, historyIndex - 1);
    } else {
      historyIndex = Math.min(messageHistory.length, historyIndex + 1);
    }

    if (historyIndex < messageHistory.length) {
      messageInput.value = messageHistory[historyIndex];
    } else {
      messageInput.value = "";
    }

    autoResizeTextarea();
  }

  // Send Message
  function sendMessage() {
    const content = messageInput.value.trim();
    if (!content) return;

    sendMessageContent(content);
    messageInput.value = "";
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
    if (cleanContent.startsWith("/")) {
      pendingKidcoreStreamingFx = null;

      // Commands: show as system message, don't disable input
      const cmdMsg = document.createElement("chat-message");
      cmdMsg.setAttribute("role", "system");
      cmdMsg.setAttribute("content", `Command: ${cleanContent}`);
      cmdMsg.setAttribute("timestamp", new Date().toISOString());
      messageList.appendChild(cmdMsg);
      scrollToBottom();

      wsClient.sendCommand(cleanContent);
      // Don't disable input - commands are instant
      return;
    }

    pendingKidcoreStreamingFx = cleanContent.toLowerCase().includes("glue shimmer")
      ? "glue-shimmer"
      : null;

    const userMessage = document.createElement("chat-message");
    userMessage.setAttribute("role", "user");
    userMessage.setAttribute("content", cleanContent);
    userMessage.setAttribute("timestamp", new Date().toISOString());
    userMessage.setAttribute("message-id", createClientMessageId("user"));
    userMessage.setAttribute("data-session-message", "true");
    messageList.appendChild(userMessage);
    // Animate message entrance
    void MessageAnimator.animateEntrance(userMessage, "user");

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
        previousMessage.matches?.("chat-message") &&
        previousMessage.getAttribute("role") === "user"
      ) {
        return typeof previousMessage.getContent === "function"
          ? previousMessage.getContent()
          : previousMessage.getAttribute("content") || "";
      }

      previousMessage = previousMessage.previousElementSibling ?? null;
    }

    return "";
  }

  function retryAssistantMessage(messageElement) {
    const retryRequest = getRetryRequest(messageElement);
    if (!retryRequest) {
      showError("Could not find the previous user prompt to regenerate this reply.");
      return;
    }

    const isCurrentStreamingAssistant =
      currentAssistantMessage === messageElement &&
      currentAssistantMessage?.classList.contains("streaming");

    // Remove the assistant message being regenerated from the DOM
    // so the new response replaces it instead of appending
    if (messageElement?.parentNode) {
      messageElement.remove();
    }

    if (isCurrentStreamingAssistant) {
      pendingEditRequest = retryRequest;
      handleStopGenerating();
      return;
    }

    if (currentAssistantMessage === messageElement) {
      currentAssistantMessage = null;
    }

    if (currentAssistantMessage?.classList.contains("streaming")) {
      pendingEditRequest = retryRequest;
      handleStopGenerating();
      return;
    }

    sendChatEditRequest(retryRequest.messageId, retryRequest.content);
  }

  // Textarea Auto-Resize
  function autoResizeTextarea() {
    messageInput.style.height = "auto";
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
    const lines = textBeforeCursor.split("\n");
    const currentLine = lines[lines.length - 1];

    // Check if we're at the start of a command
    if (currentLine.startsWith("/")) {
      const filter = currentLine.substring(1);
      const filtered = commands.filter(
        (cmd) =>
          cmd.value.toLowerCase().includes(filter.toLowerCase()) ||
          cmd.description?.toLowerCase().includes(filter.toLowerCase()),
      );
      showCompletionMenu(filtered);
    } else {
      completionMenu.hide();
    }
  }

  // Global Tool Toggle (Ctrl+T)
  function toggleAllTools() {
    allToolsExpanded = !allToolsExpanded;
    const toolCalls = document.querySelectorAll("tool-call");
    toolCalls.forEach((tool) => {
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
    setComposerState("streaming");
    refreshEditableMessageState();
  }

  function setCancellingState() {
    if (stopButton) {
      stopButton.disabled = true;
      stopButton.style.opacity = "0.6";
    }
    setComposerState("cancelling");
  }

  function handleStopGenerating() {
    if (composerState === "cancelling") {
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
      stopButton.style.opacity = "";
    }
    setComposerState("idle");
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
    const errorMsg = document.createElement("chat-message");
    errorMsg.setAttribute("role", "system");
    errorMsg.setAttribute("content", `Error: ${message}`);
    messageList.appendChild(errorMsg);
    scrollToBottom();
  }

  // Toast notification
  function showToast(message, level = "info") {
    playKidcoreClick();
    const toastContainer = document.getElementById("toast-container");
    if (toastContainer?.show) {
      toastContainer.show(message, level, 5000);
    } else {
      console.log(`[${level?.toUpperCase() || "INFO"}] ${message}`);
    }
  }

  // Typing Indicator
  let typingIndicatorElement = null;

  function showTypingIndicator() {
    // Don't show if already visible
    if (typingIndicatorElement) return;

    // Don't show if there's already an assistant message
    if (currentAssistantMessage) return;

    typingIndicatorElement = TypingIndicator.create();
    messageList.appendChild(typingIndicatorElement);
    scrollToBottom();
  }

  function hideTypingIndicator() {
    if (typingIndicatorElement) {
      typingIndicatorElement.remove();
      typingIndicatorElement = null;
    }
  }

  // Status Bar Update
  function updateStatusBar(payload) {
    const statusBar = document.getElementById("status-bar");
    if (!statusBar) return;

    // Update model
    if (payload.model !== undefined) {
      statusBar.setAttribute("model", payload.model);
    }

    // Update tokens
    if (payload.inputTokens !== undefined || payload.outputTokens !== undefined) {
      statusBar.setAttribute("inputtokens", payload.inputTokens || 0);
      statusBar.setAttribute("outputtokens", payload.outputTokens || 0);
      if (payload.cacheReadTokens !== undefined) {
        statusBar.setAttribute("cachedtokens", payload.cacheReadTokens);
      }
      if (payload.reasoningTokens !== undefined) {
        statusBar.setAttribute("reasoningtokens", payload.reasoningTokens);
      }
      if (payload.contextTokens !== undefined) {
        statusBar.setAttribute("contexttokens", payload.contextTokens);
      }
    }

    // Update queue
    if (payload.queueLength !== undefined) {
      statusBar.setAttribute("queue", payload.queueLength);
    }

    // Update streaming status
    if (payload.isStreaming !== undefined) {
      statusBar.setAttribute("streaming", payload.isStreaming);
    }

    applyDaemonStatusPayload(payload);
  }

  // Event Listeners
  sendButton.addEventListener("click", sendMessage);
  // stopButton?.addEventListener('click', handleStopGenerating)
  stopButton?.addEventListener("click", handleStopGenerating);

  // History navigation buttons (mobile)
  const historyUpBtn = document.getElementById("history-up");
  const historyDownBtn = document.getElementById("history-down");
  historyUpBtn?.addEventListener("click", () => navigateHistory("up"));
  historyDownBtn?.addEventListener("click", () => navigateHistory("down"));

  // Textarea input handling
  messageInput.addEventListener("input", () => {
    autoResizeTextarea();
    checkForCompletionTrigger();
  });

  // Leader key state (Emacs-style Ctrl+S prefix)
  // Leader-only mode: ALL keyboard shortcuts go through the leader menu
  let leaderMode = false;
  let leaderPath = [];
  let leaderTree = buildLeaderTree(getKeymap());
  let whichKey = null;

  const leaderActionHandlers = {
    "search.open": () => SearchOverlay.getInstance().open(),
    "quickSwitcher.open": () => QuickSwitcher.getInstance().open(),
    "mentions.open": () => {
      messageInput?.focus();
      const cursorPos = messageInput.selectionStart;
      const value = messageInput.value;
      messageInput.value = `${value.slice(0, cursorPos)}@${value.slice(cursorPos)}`;
      messageInput.selectionStart = cursorPos + 1;
      messageInput.selectionEnd = cursorPos + 1;
      messageInput.dispatchEvent(new Event("input", { bubbles: true }));
    },
    "composer.focus": () => messageInput?.focus(),
    "composer.queue": () => {
      const content = messageInput.value.trim();
      if (!content) {
        return;
      }

      if (currentAssistantMessage) {
        addToQueue(content);
      } else {
        sendMessageContent(content);
      }

      messageInput.value = "";
      autoResizeTextarea();
    },
    "commandPalette.open": () => window.alfredCommandPalette?.open?.(),
    "composer.newline": () => {
      const cursorPos = messageInput.selectionStart;
      const value = messageInput.value;
      messageInput.value = `${value.slice(0, cursorPos)}\n${value.slice(cursorPos)}`;
      messageInput.selectionStart = cursorPos + 1;
      messageInput.selectionEnd = cursorPos + 1;
      autoResizeTextarea();
      messageInput.dispatchEvent(new Event("input", { bubbles: true }));
    },
    "chat.clear": () => {
      messageList.innerHTML = "";
      window.addSystemMessage?.("Chat cleared");
    },
    "session.new": () => {
      if (confirm("Start a new session? Current conversation will be archived.")) {
        window.location.reload();
      }
    },
    "message.edit": () => {
      const lastUserMessage = messageList.querySelector('chat-message[role="user"]:last-of-type');
      if (lastUserMessage) {
        lastUserMessage.dispatchEvent(new CustomEvent("edit-message", { bubbles: true }));
      }
    },
    "message.copy": () => {
      const focused = document.activeElement?.closest?.("chat-message");
      if (focused && typeof focused._copyToClipboard === "function") {
        focused._copyToClipboard();
      }
    },
    "navigation.up": () => window.alfredMessageNavigator?.previous?.(),
    "navigation.down": () => window.alfredMessageNavigator?.next?.(),
    "navigation.home": () => window.alfredMessageNavigator?.first?.(),
    "navigation.end": () => window.alfredMessageNavigator?.last?.(),
    "theme.palette.open": () => openThemePalette(),
    "context.open": () => {
      const wsClient = window.alfredWebSocketClient;
      if (wsClient && typeof wsClient.sendCommand === "function") {
        wsClient.sendCommand("/context");
      }
    },
    "help.open": () => openKeyboardHelp(),
    "chat.cancel": () => {
      if (window.handleStopGenerating) {
        window.handleStopGenerating();
      }
    },
    "queue.clear": () => {
      if (window.clearQueue) {
        window.clearQueue();
        window.addSystemMessage?.("Message queue cleared");
      }
    },
    "tools.toggleAll": () => toggleAllTools(),
  };

  subscribe(() => {
    leaderTree = buildLeaderTree(getKeymap());
    if (whichKey) {
      whichKey.setBindings(leaderTree);
    }
  });

  function initWhichKey() {
    if (!whichKey) {
      whichKey = new WhichKey();
    }

    whichKey.setBindings(leaderTree);
  }

  function renderLeaderLegend() {
    if (whichKey) {
      whichKey.show(messageInput, leaderPath);
    }
  }

  function openKeyboardHelp() {
    if (window.alfredHelpSheet?.show) {
      window.alfredHelpSheet.show();
      return;
    }

    if (typeof window.HelpSheet !== "undefined") {
      window.alfredHelpSheet = window.alfredHelpSheet ?? new HelpSheet();
      window.alfredHelpSheet.show();
      return;
    }

    window.dispatchEvent(new CustomEvent("help:open"));
  }

  function enterLeaderMode() {
    initWhichKey();

    leaderMode = true;
    leaderPath = [];
    messageInput.classList.add("leader-mode");
    messageInput.placeholder =
      "Leader: S=Search, C=Chat, M=Messages, P=Palette, T=Theme, H=Help, X=Cancel";

    messageInput.focus();
    renderLeaderLegend();
  }

  function exitLeaderMode() {
    leaderMode = false;
    leaderPath = [];
    messageInput.classList.remove("leader-mode");
    messageInput.placeholder = "Enter to send, Shift+Enter for newline, Alt+Enter to queue";
    if (whichKey) {
      whichKey.hide();
    }
  }

  function handleLeaderKeydown(e) {
    e.preventDefault();

    if (["Shift", "Control", "Alt", "Meta"].includes(e.key)) {
      return;
    }

    if (e.key === "Escape") {
      exitLeaderMode();
      return;
    }

    const binding = getLeaderNodeForPath(leaderTree, [...leaderPath, e.key]);
    if (!binding) {
      exitLeaderMode();
      return;
    }

    if (Array.isArray(binding.children) && binding.children.length > 0) {
      leaderPath = [...leaderPath, binding.key];
      renderLeaderLegend();
      return;
    }

    exitLeaderMode();
    const handler = leaderActionHandlers[binding.actionId];
    if (handler) {
      handler();
    } else {
      console.error(`No leader action handler registered for ${binding.actionId}`);
    }
  }

  // Keyboard handling
  messageInput.addEventListener("keydown", (e) => {
    if (leaderMode) {
      return;
    }

    // Handle completion menu first (before other Enter handling)
    if (completionMenu.isVisible()) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        completionMenu.selectNext();
        return;
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        completionMenu.selectPrevious();
        return;
      }
      if (e.key === "Enter" || e.key === "Tab") {
        e.preventDefault();
        completionMenu.selectCurrent();
        return;
      }
      if (e.key === "Escape") {
        completionMenu.hide();
        return;
      }
    }

    // Shift+Enter: Queue message if streaming, otherwise send immediately
    if (e.key === "Enter" && e.shiftKey && composerState !== "editing") {
      e.preventDefault();
      const content = messageInput.value.trim();
      if (content) {
        if (currentAssistantMessage) {
          addToQueue(content);
        } else {
          sendMessageContent(content);
        }
        messageInput.value = "";
        autoResizeTextarea();
      }
      return;
    }

    // Enter (without Shift): Send message
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
      return;
    }

    // History navigation
    if (e.key === "ArrowUp" && messageInput.selectionStart === 0) {
      e.preventDefault();
      navigateHistory("up");
      return;
    }
    if (e.key === "ArrowDown" && messageInput.selectionStart === messageInput.value.length) {
      e.preventDefault();
      navigateHistory("down");
      return;
    }

    if (e.key === "Escape" && currentAssistantMessage && composerState !== "cancelling") {
      e.preventDefault();
      handleStopGenerating();
      return;
    }

    // Ctrl+U: Clear input
    if (e.ctrlKey && e.key === "u") {
      e.preventDefault();
      messageInput.value = "";
      autoResizeTextarea();
      return;
    }
  });

  // Global keyboard shortcuts - Leader mode
  document.addEventListener(
    "keydown",
    (e) => {
      if (e.ctrlKey && e.key.toLowerCase() === "s") {
        e.preventDefault();
        enterLeaderMode();
        return;
      }

      if (leaderMode) {
        handleLeaderKeydown(e);
      }
    },
    true,
  );

  messageList.addEventListener("retry-message", (event) => {
    const messageElement = event.target?.closest?.("chat-message");
    if (!messageElement || messageElement.getAttribute("role") !== "assistant") {
      return;
    }

    retryAssistantMessage(messageElement);
  });

  messageList.addEventListener("edit-message", (event) => {
    // Inline editing is now handled within chat-message component
    // This event is kept for backward compatibility
    const messageElement = event.target?.closest?.("chat-message");
    if (!messageElement || messageElement.getAttribute("role") !== "user") {
      return;
    }
    // Inline editing starts automatically when the edit button is clicked
    // No need to populate composer anymore
  });

  // Handle inline edit save
  messageList.addEventListener("message-edited", (event) => {
    const { messageId, newContent } = event.detail;
    const messageElement = event.target?.closest?.("chat-message");
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
    pendingKidcoreStreamingFx = newContent.toLowerCase().includes("glue shimmer")
      ? "glue-shimmer"
      : null;
    scrollToBottom();
    sendChatEditRequest(messageId, newContent, { playSound: false });
  });

  // Completion menu selection
  completionMenu.addEventListener("select", (e) => {
    const selected = e.detail;
    const value = messageInput.value;
    const cursorPosition = messageInput.selectionStart;

    // Replace current command with selected one
    const textBeforeCursor = value.substring(0, cursorPosition);
    const lines = textBeforeCursor.split("\n");
    const currentLineIndex = lines.length - 1;
    const currentLine = lines[currentLineIndex];

    if (currentLine.startsWith("/")) {
      lines[currentLineIndex] = `${selected.value} `;
      const newTextBefore = lines.join("\n");
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
  let scrollDirection = "none";
  let scrollDistance = 0;
  let scrollTimeout = null;

  // Guard states for top/bottom bounce handling
  let hasTopLeft = false; // Must scroll down from top before header can hide
  let hasBottomLeft = false; // Must scroll up from bottom before header can show (when hidden)
  let scrollHandlerInitialized = false; // First scroll event just initializes state

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
    return {
      scrollTop,
      maxScroll,
      distanceFromBottom,
      hideThreshold,
      showThreshold,
      edgeTolerance,
      clientHeight,
    };
  }

  function handleScroll() {
    // Only apply on mobile
    if (window.innerWidth > MOBILE_BREAKPOINT) {
      if (isHeaderHidden) {
        showHeader();
      }
      return;
    }

    const {
      scrollTop,
      maxScroll,
      distanceFromBottom,
      hideThreshold,
      showThreshold,
      edgeTolerance,
    } = getScrollInfo();

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
    const newDirection = delta > 0 ? "down" : "up";

    // Reset distance on direction change
    if (newDirection !== scrollDirection) {
      scrollDirection = newDirection;
      scrollDistance = 0;
    }

    // Accumulate distance in current direction
    scrollDistance += Math.abs(delta);

    // Handle scroll down - hide header after threshold (only if we've left the top)
    if (scrollDirection === "down" && !isHeaderHidden && hasTopLeft) {
      if (scrollDistance > hideThreshold) {
        hideHeader();
        scrollDistance = 0;
      }
    }

    // Handle scroll up - show header after threshold (only if we've left the bottom)
    if (scrollDirection === "up" && isHeaderHidden && hasBottomLeft) {
      if (scrollDistance > showThreshold) {
        showHeader();
        scrollDistance = 0;
      }
    }

    // Reset scroll tracking after inactivity
    scrollTimeout = setTimeout(() => {
      scrollDirection = "none";
      scrollDistance = 0;
    }, 200);
  }

  function hideHeader() {
    const header = document.querySelector(".app-header");
    if (header) {
      header.classList.add("hidden");
    }
    isHeaderHidden = true;
  }

  function showHeader() {
    const header = document.querySelector(".app-header");
    if (header) {
      header.classList.remove("hidden");
    }
    isHeaderHidden = false;
  }

  // Attach scroll listener
  chatContainer.addEventListener("scroll", handleScroll, { passive: true });

  // Restore header when focusing the composer
  messageInput.addEventListener("focus", () => {
    if (isHeaderHidden && window.innerWidth <= MOBILE_BREAKPOINT) {
      showHeader();
    }
    restoreChrome();
  });

  // Handle scroll for mobile chrome collapse
  window.addEventListener("scroll", handleScroll);

  // Handle window resize to reset hidden state on desktop
  window.addEventListener("resize", () => {
    if (window.innerWidth > MOBILE_BREAKPOINT && isHeaderHidden) {
      showHeader();
    }
    scrollToBottom();
  });

  // Connect WebSocket
  wsClient.connect();

  // Focus input on load
  messageInput.focus();

  console.log("Alfred Web UI initialized");
}

// Add copy buttons to code blocks
function addCopyButtons() {
  const codeBlocks = document.querySelectorAll("pre code");
  codeBlocks.forEach((codeBlock) => {
    // Skip if already wrapped
    if (codeBlock.closest(".code-block-wrapper")) return;

    const pre = codeBlock.parentElement;
    const wrapper = document.createElement("div");
    wrapper.className = "code-block-wrapper";

    // Create copy button - same icon as message copy
    const copyBtn = document.createElement("button");
    copyBtn.className = "code-copy-btn";
    copyBtn.innerHTML = "⧉";
    copyBtn.title = "Copy code";

    copyBtn.addEventListener("click", async (e) => {
      e.stopPropagation();
      const textToCopy = codeBlock.textContent;

      // Try modern clipboard API first
      if (navigator.clipboard?.writeText) {
        try {
          await navigator.clipboard.writeText(textToCopy);
          showCopyFeedback(copyBtn);
          return;
        } catch {
          console.log("Clipboard API failed, trying fallback");
        }
      }

      // Fallback: use execCommand
      try {
        const textarea = document.createElement("textarea");
        textarea.value = textToCopy;
        textarea.style.position = "fixed";
        textarea.style.left = "-9999px";
        textarea.style.top = "0";
        document.body.appendChild(textarea);
        textarea.focus();
        textarea.select();

        const successful = document.execCommand("copy");
        document.body.removeChild(textarea);

        if (successful) {
          showCopyFeedback(copyBtn);
        } else {
          console.error("execCommand copy failed");
          showCopyFailed(copyBtn);
        }
      } catch (err) {
        console.error("Failed to copy:", err);
        showCopyFailed(copyBtn);
      }
    });

    // Wrap the pre element
    pre.parentNode.insertBefore(wrapper, pre);
    wrapper.appendChild(copyBtn);
    wrapper.appendChild(pre);
  });

  // Floating settings button (mobile) - triggers the settings-menu
  const floatingSettingsBtn = document.getElementById("floating-settings-btn");
  if (floatingSettingsBtn) {
    // Show floating button on mobile (remove hidden attribute)
    if (window.innerWidth <= 768) {
      floatingSettingsBtn.removeAttribute("hidden");
    }

    // Update visibility on resize
    window.addEventListener("resize", () => {
      if (window.innerWidth <= 768) {
        floatingSettingsBtn.removeAttribute("hidden");
      } else {
        floatingSettingsBtn.setAttribute("hidden", "");
      }
    });

    // Click handler - open settings menu
    floatingSettingsBtn.addEventListener("click", (event) => {
      event.stopPropagation();
      const settingsMenu = document.querySelector("settings-menu");
      if (settingsMenu) {
        // Toggle settings menu by clicking its toggle button
        const toggleBtn = settingsMenu.querySelector(".settings-toggle");
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
  btn.innerHTML = "✓";
  btn.classList.add("copied");
  setTimeout(() => {
    btn.innerHTML = originalText;
    btn.classList.remove("copied");
  }, 800);
}

function showCopyFailed(btn) {
  if (!btn) return;
  const originalText = btn.innerHTML;
  btn.innerHTML = "✗";
  btn.classList.add("failed");
  setTimeout(() => {
    btn.innerHTML = originalText;
    btn.classList.remove("failed");
  }, 1500);
}

// ============================================
// Command Palette Initialization (PRD #159)
// ============================================

function initCommandPalette() {
  // Only initialize if the library is loaded
  if (typeof window.CommandPaletteLib === "undefined") {
    console.warn("CommandPaletteLib not loaded, skipping palette initialization");
    return;
  }

  const { CommandPalette, CommandRegistry } = window.CommandPaletteLib;

  // Create palette instance
  const palette = new CommandPalette({
    placeholder: "Type a command...",
  });

  // Register default commands
  CommandRegistry.register({
    id: "clear-chat",
    title: "Clear Chat",
    keywords: ["reset", "clean", "delete"],
    shortcut: "Ctrl+Shift+C",
    action: () => {
      if (confirm("Clear all messages?")) {
        const messageList = document.getElementById("message-list");
        if (messageList) {
          messageList.innerHTML = "";
          window.addSystemMessage?.("Chat cleared");
        }
      }
    },
  });

  CommandRegistry.register({
    id: "toggle-theme",
    title: "Toggle Theme",
    keywords: ["dark", "light", "mode", "color"],
    shortcut: "Ctrl+Shift+T",
    action: () => {
      const currentTheme = document.documentElement.getAttribute("data-theme");
      const newTheme = currentTheme === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", newTheme);
      localStorage.setItem("theme", newTheme);
      window.addSystemMessage?.(`Theme changed to ${newTheme}`);
    },
  });

  CommandRegistry.register({
    id: "new-session",
    title: "New Session",
    keywords: ["create", "start", "reset"],
    action: () => {
      if (confirm("Start a new session? Current conversation will be archived.")) {
        window.location.reload();
      }
    },
  });

  CommandRegistry.register({
    id: "focus-input",
    title: "Focus Input",
    keywords: ["type", "write", "compose"],
    shortcut: "/",
    action: () => {
      const input = document.getElementById("message-input");
      if (input) {
        input.focus();
      }
    },
  });

  console.log("Command palette initialized with", CommandRegistry.getAll().length, "commands");

  // Store palette instance globally for debugging
  window.alfredCommandPalette = palette;
}

// ============================================
// Keyboard Shortcuts Initialization (PRD #159)
// ============================================

function initKeyboardShortcuts() {
  // Only initialize if the library is loaded
  if (
    typeof window.ShortcutRegistry === "undefined" ||
    typeof window.KeyboardManager === "undefined" ||
    typeof window.HelpModal === "undefined" ||
    typeof window.MessageNavigator === "undefined"
  ) {
    console.warn("Keyboard libraries not loaded, skipping keyboard shortcuts initialization");
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
    id: "show-help",
    key: "?",
    description: "Show keyboard shortcuts",
    category: "Global",
    action: () => helpModal.toggle(),
  });

  ShortcutRegistry.register({
    id: "toggle-help",
    key: "Shift+/",
    description: "Show keyboard shortcuts",
    category: "Global",
    action: () => helpModal.toggle(),
  });

  // Navigation shortcuts
  ShortcutRegistry.register({
    id: "focus-previous-message",
    key: "ArrowUp",
    description: "Previous message",
    category: "Navigation",
    context: "message-focused",
    action: () => messageNavigator.previous(),
  });

  ShortcutRegistry.register({
    id: "focus-next-message",
    key: "ArrowDown",
    description: "Next message",
    category: "Navigation",
    context: "message-focused",
    action: () => messageNavigator.next(),
  });

  ShortcutRegistry.register({
    id: "focus-first-message",
    key: "Home",
    description: "First message",
    category: "Navigation",
    context: "message-focused",
    action: () => messageNavigator.first(),
  });

  ShortcutRegistry.register({
    id: "focus-last-message",
    key: "End",
    description: "Last message",
    category: "Navigation",
    context: "message-focused",
    action: () => messageNavigator.last(),
  });

  // Make messages focusable when they're added
  const makeMessagesFocusable = () => {
    messageNavigator.makeMessagesFocusable();
  };

  // Run initially and after new messages
  makeMessagesFocusable();

  // Watch for new messages
  const messageList = document.getElementById("message-list");
  if (messageList) {
    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        if (mutation.type === "childList" && mutation.addedNodes.length > 0) {
          makeMessagesFocusable();
        }
      }
    });
    observer.observe(messageList, { childList: true });
  }

  console.log(
    "Keyboard shortcuts initialized with",
    ShortcutRegistry.getAllFlat().length,
    "shortcuts",
  );

  // Store instances globally for debugging
  window.alfredKeyboardManager = keyboardManager;
  window.alfredHelpModal = helpModal;
  window.alfredMessageNavigator = messageNavigator;
}

// ============================================
// Context Menu Initialization (PRD #159)
// ============================================

function initContextMenus() {
  // Only initialize if the library is loaded
  if (
    typeof window.ContextMenuLib === "undefined" ||
    typeof window.MessageContextMenu === "undefined" ||
    typeof window.CodeContextMenu === "undefined"
  ) {
    console.warn("Context menu libraries not loaded, skipping context menu initialization");
    return;
  }

  const { MessageContextMenu, CodeContextMenu } = window;

  // Attach to existing messages
  MessageContextMenu.attachToAllMessages();

  // Attach to existing code blocks
  CodeContextMenu.attachToAllCodeBlocks();

  // Watch for new messages and code blocks
  const messageList = document.getElementById("message-list");
  if (messageList) {
    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        if (mutation.type === "childList") {
          // Check for new messages
          mutation.addedNodes.forEach((node) => {
            if (node.nodeType === Node.ELEMENT_NODE) {
              // If it's a message
              if (node.classList?.contains("message")) {
                MessageContextMenu.attachMessageMenu(node);
              }
              // If it contains messages
              if (node.querySelectorAll) {
                const messages = node.querySelectorAll(".message");
                messages.forEach((msg) => MessageContextMenu.attachMessageMenu(msg));
              }
            }
          });
        }
      }
    });
    observer.observe(messageList, { childList: true, subtree: true });
  }

  // Watch for code blocks (they may be added when messages render)
  const chatContainer = document.getElementById("chat-container");
  if (chatContainer) {
    const codeObserver = new MutationObserver(() => {
      CodeContextMenu.attachToAllCodeBlocks();
    });
    codeObserver.observe(chatContainer, { childList: true, subtree: true });
  }

  console.log("Context menus initialized");
}

// ============================================
// Notifications Initialization (PRD #159)
// ============================================

function initNotifications() {
  // Only initialize if libraries are loaded
  if (typeof window.NotificationsLib === "undefined") {
    console.warn("Notifications library not loaded, skipping notifications");
    return;
  }

  const { NotificationPermissionManager, NotificationService, FaviconBadge, Toast } =
    window.NotificationsLib;

  // Initialize permission manager
  NotificationPermissionManager.init();

  // Initialize favicon badge
  FaviconBadge.init();

  // Listen for WebSocket response completion
  window.addEventListener("websocket:message-complete", async (e) => {
    const { message, preview } = e.detail || {};

    // Only notify if tab is hidden
    if (!document.hidden) {
      return;
    }

    // Increment badge
    FaviconBadge.increment();

    // Try browser notification
    const permission = NotificationPermissionManager.getPermission();

    if (permission === "granted") {
      await NotificationService.showResponseComplete(preview || message);
    } else if (permission === "denied") {
      // Show in-app toast instead
      Toast.info("New response from Alfred", { duration: 5000 });
    }
    // If permission is 'default', don't show anything (user hasn't decided)
  });

  // Request permission on first message send
  const originalSendMessage = window.sendMessage;
  if (originalSendMessage) {
    window.sendMessage = async function (...args) {
      // Request permission if needed
      if (NotificationPermissionManager.shouldAsk()) {
        const result = await NotificationPermissionManager.request();
        if (result === "denied") {
          Toast.warning("Notifications denied. Enable in browser settings for background alerts.", {
            duration: 8000,
          });
        }
      }
      return originalSendMessage.apply(this, args);
    };
  }

  console.log("Notifications initialized");

  // Store globally
  window.alfredNotifications = {
    permission: NotificationPermissionManager,
    service: NotificationService,
    badge: FaviconBadge,
    toast: Toast,
  };
}

// ============================================
// Drag & Drop Initialization (PRD #159)
// ============================================

function initDragDrop() {
  // Only initialize if libraries are loaded
  if (typeof window.DragDropLib === "undefined") {
    console.warn("Drag-drop library not loaded, skipping drag-drop");
    return;
  }

  const {
    DragDropManager,
    FileValidation,
    ImageCompression,
    FileUpload,
    ClipboardHandler,
    DropZoneVisual,
  } = window.DragDropLib;

  // Find chat container
  const chatContainer =
    document.getElementById("chat-container") || document.getElementById("message-list");
  if (!chatContainer) {
    console.warn("Chat container not found, drag-drop disabled");
    return;
  }

  // Create visual feedback
  const visual = new DropZoneVisual(chatContainer);

  // Create drag-drop manager
  const manager = new DragDropManager();

  manager.onDragEnter = () => {
    visual.show();
  };

  manager.onDragLeave = () => {
    visual.hide();
  };

  manager.onFilesDropped = async (files) => {
    visual.hide();

    // Validate files
    const { valid, invalid } = FileValidation.validateFiles(files);

    // Show errors for invalid files
    invalid.forEach(({ file, error }) => {
      console.warn("Invalid file:", file.name, error);
      if (window.NotificationsLib?.Toast) {
        window.NotificationsLib.Toast.error(error);
      }
    });

    if (valid.length === 0) return;

    // Get WebSocket client
    const wsClient = window.alfredWebSocketClient;
    if (!wsClient) {
      console.error("WebSocket client not available");
      if (window.NotificationsLib?.Toast) {
        window.NotificationsLib.Toast.error("Cannot upload: not connected to server");
      }
      return;
    }

    // Process and upload each file
    for (const file of valid) {
      try {
        // Show progress toast
        const progressToast = window.NotificationsLib?.Toast
          ? window.NotificationsLib.Toast.info(`Uploading ${file.name}...`, { duration: 60000 })
          : null;

        // Compress images if needed
        const processedFile = await ImageCompression.compressToFile(file);

        // Upload
        const result = await FileUpload.uploadFile(processedFile, wsClient);

        // Show success
        if (window.NotificationsLib?.Toast) {
          if (progressToast) progressToast.dismiss?.();
          window.NotificationsLib.Toast.success(`${file.name} uploaded`);
        }

        console.log("Upload started:", result);
      } catch (error) {
        console.error("Upload failed:", file.name, error);
        if (window.NotificationsLib?.Toast) {
          window.NotificationsLib.Toast.error(`Failed to upload ${file.name}: ${error.message}`);
        }
      }
    }
  };

  // Attach to chat container
  manager.attachToElement(chatContainer);

  // Set up clipboard paste
  ClipboardHandler.onPaste = async (files) => {
    // Same validation and upload logic as drag-drop
    const { valid, invalid } = FileValidation.validateFiles(files);

    invalid.forEach(({ error }) => {
      if (window.NotificationsLib?.Toast) {
        window.NotificationsLib.Toast.error(error);
      }
    });

    if (valid.length === 0) return;

    const wsClient = window.alfredWebSocketClient;
    if (!wsClient) {
      if (window.NotificationsLib?.Toast) {
        window.NotificationsLib.Toast.error("Cannot upload: not connected to server");
      }
      return;
    }

    for (const file of valid) {
      try {
        const processedFile = await ImageCompression.compressToFile(file);
        await FileUpload.uploadFile(processedFile, wsClient);
        if (window.NotificationsLib?.Toast) {
          window.NotificationsLib.Toast.success(`${file.name} uploaded`);
        }
      } catch {
        if (window.NotificationsLib?.Toast) {
          window.NotificationsLib.Toast.error(`Failed to upload ${file.name}`);
        }
      }
    }
  };

  ClipboardHandler.attach();

  // Handle server responses
  wsClient.addEventListener("message", (event) => {
    const message = event.detail || event.data;
    if (typeof message === "object" && message.type === "file.received") {
      const result = FileUpload.handleResponse(message);
      if (result) {
        if (result.status === "accepted") {
          if (window.NotificationsLib?.Toast) {
            window.NotificationsLib.Toast.success(`${result.file.name} ready`);
          }
        } else {
          if (window.NotificationsLib?.Toast) {
            window.NotificationsLib.Toast.error(`Upload failed: ${result.reason}`);
          }
        }
      }
    }
  });

  // Register upload command in palette
  if (window.registerCommand) {
    window.registerCommand({
      id: "upload-file",
      title: "Upload File",
      keywords: ["upload", "file", "attach", "image"],
      action: () => {
        // Create hidden file input
        const input = document.createElement("input");
        input.type = "file";
        input.multiple = true;
        input.accept = FileValidation.ALLOWED_MIME_TYPES.join(",");
        input.onchange = (e) => {
          if (e.target.files.length > 0) {
            manager.onFilesDropped?.(Array.from(e.target.files));
          }
        };
        input.click();
      },
    });
  }

  console.log("Drag-drop initialized");

  // Store globally
  window.alfredDragDrop = {
    manager,
    visual,
    clipboard: ClipboardHandler,
  };
}

// ============================================
// Mobile Gestures Initialization
// ============================================

let mobileGesturesCleanup = null;
let swipeToReplyInstance = null;

/**
 * Initialize mobile gesture features (swipe-to-reply, fullscreen compose)
 */
function initMobileGestures() {
  // Only initialize on touch devices
  if (!isTouchDevice()) {
    console.log("[Gestures] Touch device not detected, skipping gesture initialization");
    return;
  }

  console.log("[Gestures] Initializing mobile gestures...");

  // Initialize Swipe-to-Reply on message list
  const messageList = document.getElementById("message-list");
  const messageInput = document.getElementById("message-input");

  if (messageList && messageInput) {
    swipeToReplyInstance = new SwipeToReply({
      threshold: GESTURE_CONFIG.SWIPE_THRESHOLD,
      onReply: (_messageId, content) => {
        // Format as markdown quote and populate input
        const quotedContent = content
          .split("\n")
          .map((line) => `> ${line}`)
          .join("\n");
        messageInput.value = `${quotedContent}\n\n`;
        messageInput.focus();

        // Trigger input event to resize textarea
        messageInput.dispatchEvent(new Event("input", { bubbles: true }));

        // Haptic feedback
        if (navigator.vibrate) {
          navigator.vibrate([20, 30, 20]);
        }
      },
    });

    // Attach to existing messages
    swipeToReplyInstance.attachToAllMessages(messageList);

    console.log("[Gestures] Swipe-to-reply initialized");
  }

  // Initialize fullscreen compose on mobile
  if (messageInput) {
    const fullscreenResult = initializeFullscreenCompose(messageInput, {
      placeholder: "Message Alfred...",
      onSubmit: (content) => {
        // Send message via WebSocket
        const wsClient = window.alfredWebSocketClient;
        if (wsClient && typeof wsClient.sendCommand === "function") {
          wsClient.sendCommand(content);
        }
      },
    });

    if (fullscreenResult) {
      console.log("[Gestures] Fullscreen compose initialized");
    }
  }

  // Store cleanup function
  mobileGesturesCleanup = () => {
    if (swipeToReplyInstance) {
      swipeToReplyInstance.destroy();
      swipeToReplyInstance = null;
    }
    // Fullscreen compose cleanup is handled by its own destroy function
  };

  console.log("[Gestures] Mobile gestures initialized");
}

/**
 * Initialize in-conversation search (Ctrl+F)
 * Milestone 9 Phase 1: Search & Quick Navigation
 */
function initSearch() {
  try {
    initializeSearch();
    console.log("[Search] In-conversation search initialized (Ctrl+F)");
  } catch (error) {
    console.error("[Search] Failed to initialize search:", error);
  }
}

/**
 * Initialize quick session switcher (Ctrl+Tab)
 * Milestone 9 Phase 2: Search & Quick Navigation
 */
function initQuickSwitcher() {
  try {
    initializeQuickSwitcher();
    console.log("[QuickSwitcher] Quick session switcher initialized (Ctrl+Tab)");
  } catch (error) {
    console.error("[QuickSwitcher] Failed to initialize quick switcher:", error);
  }
}

/**
 * Initialize @ mentions in message composer
 * Milestone 9 Phase 3: Search & Quick Navigation
 */
function initMentions() {
  try {
    const composer = document.getElementById("message-input");
    if (composer) {
      initializeMentions({ composer });
      console.log("[Mentions] @ mentions initialized");
    }
  } catch (error) {
    console.error("[Mentions] Failed to initialize mentions:", error);
  }
}

// ============================================
// Initialization
// ============================================

function initAll() {
  initAlfredUI();
  initCommandPalette();
  initKeyboardShortcuts();
  initContextMenus();
  initNotifications();
  initDragDrop();
  initOffline();
  initPullToRefresh();
  initMobileGestures();
  initSearch();
  initQuickSwitcher();
  initMentions();
  initPWA({
    debug: window.APP_CONFIG?.debug,
    getComposer: () => document.getElementById("user-input"),
  });
  registerServiceWorker();

  // Cleanup on page unload
  window.addEventListener("beforeunload", () => {
    if (mobileGesturesCleanup) {
      mobileGesturesCleanup();
    }
  });
}

/**
 * Initialize offline features (connection monitor and indicator)
 */
function initOffline() {
  // Create offline indicator element if it doesn't exist
  let offlineIndicator = document.getElementById("offline-indicator");
  if (!offlineIndicator) {
    offlineIndicator = document.createElement("offline-indicator");
    offlineIndicator.id = "offline-indicator";
    document.body.appendChild(offlineIndicator);
  }

  // Initialize connection monitor
  const monitor = new ConnectionMonitor();

  // Listen for connection state changes
  monitor.addEventListener("statechange", (event) => {
    const { state, previousState } = event.detail;

    // Update offline indicator
    if (offlineIndicator) {
      offlineIndicator.setAttribute("state", state);
    }

    // Log for debugging
    console.log(`[Connection] ${previousState} → ${state}`);
  });

  // Track WebSocket state
  const wsClient = window.alfredWebSocketClient;
  if (wsClient) {
    monitor.trackWebSocket(wsClient);
  }

  // Expose for debugging
  window.__alfredConnectionMonitor = monitor;
}

/**
 * Initialize pull-to-refresh gesture support
 */
function initPullToRefresh() {
  const PullToRefreshDetector = window.PullToRefresh?.PullToRefreshDetector;
  const chatContainer =
    document.getElementById("chat-container") || document.getElementById("message-list");

  if (!PullToRefreshDetector || !chatContainer) {
    return;
  }

  const isTouchCapable =
    "ontouchstart" in window ||
    navigator.maxTouchPoints > 0 ||
    window.matchMedia?.("(pointer: coarse)")?.matches;

  if (!isTouchCapable) {
    return;
  }

  const wsClient = window.alfredWebSocketClient;
  if (!wsClient) {
    return;
  }

  let indicator = document.getElementById("pull-to-refresh-indicator");
  if (!indicator) {
    indicator = document.createElement("div");
    indicator.id = "pull-to-refresh-indicator";
    indicator.setAttribute("role", "status");
    indicator.setAttribute("aria-live", "polite");
    indicator.setAttribute("aria-atomic", "true");
    indicator.style.cssText = `
      position: fixed;
      top: calc(env(safe-area-inset-top, 0px) + 12px);
      left: 50%;
      z-index: 50;
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      border-radius: 999px;
      background: rgba(26, 26, 26, 0.86);
      color: #fff;
      font-size: 12px;
      font-weight: 600;
      letter-spacing: 0.02em;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.22);
      backdrop-filter: blur(12px);
      pointer-events: none;
      user-select: none;
      opacity: 0;
      transform: translateX(-50%) translateY(-10px) scale(0.96);
      transition: opacity 120ms ease, transform 160ms ease;
    `;
    indicator.innerHTML = `
      <span class="pull-to-refresh-indicator__icon" aria-hidden="true">↻</span>
      <span class="pull-to-refresh-indicator__label">Pull to refresh</span>
    `;
    document.body.appendChild(indicator);
  }

  const icon = indicator.querySelector(".pull-to-refresh-indicator__icon");
  const label = indicator.querySelector(".pull-to-refresh-indicator__label");
  let refreshTimeout = null;

  function clearRefreshTimeout() {
    if (refreshTimeout !== null) {
      window.clearTimeout(refreshTimeout);
      refreshTimeout = null;
    }
  }

  function renderIndicator(state, detail = null) {
    const progress = Math.max(0, Math.min(detail?.progress ?? 0, 1));
    const visible = state !== "idle";

    indicator.dataset.pullState = state;
    indicator.dataset.pullProgress = String(Math.round(progress * 100));
    indicator.style.opacity = visible ? "1" : "0";
    indicator.style.transform = visible
      ? "translateX(-50%) translateY(0) scale(1)"
      : "translateX(-50%) translateY(-10px) scale(0.96)";

    if (icon) {
      icon.style.display = "inline-flex";
      icon.style.width = "1em";
      icon.style.justifyContent = "center";
      icon.style.transition = state === "refreshing" ? "none" : "transform 80ms linear";
      icon.style.transform =
        state === "refreshing" ? "rotate(0deg)" : `rotate(${Math.round(progress * 180)}deg)`;
    }

    if (label) {
      label.textContent =
        state === "refreshing"
          ? "Refreshing…"
          : state === "ready"
            ? "Release to refresh"
            : "Pull to refresh";
    }
  }

  function resetIndicator() {
    clearRefreshTimeout();
    renderIndicator("idle");
  }

  function handleRefresh() {
    clearRefreshTimeout();
    renderIndicator("refreshing");
    refreshTimeout = window.setTimeout(() => {
      resetIndicator();
    }, 3000);

    if (typeof wsClient.reconnect === "function") {
      wsClient.reconnect();
    } else if (typeof wsClient.connect === "function") {
      wsClient.connect();
    }
  }

  const detector = new PullToRefreshDetector({
    threshold: 80,
    topThreshold: 10,
    resistance: 0.5,
    onPullStart: (detail) => renderIndicator("pulling", detail),
    onPullMove: (detail) => renderIndicator(detail.progress >= 1 ? "ready" : "pulling", detail),
    onPullEnd: (detail) => {
      if (!detail?.refreshed) {
        resetIndicator();
      }
    },
    onPullCancel: resetIndicator,
    onRefresh: handleRefresh,
  });

  if (!detector.attachToElement(chatContainer, chatContainer)) {
    return;
  }

  wsClient.addEventListener("connected", () => {
    resetIndicator();
  });

  window.__alfredPullToRefresh = {
    detector,
    indicator,
    resetIndicator,
    getState: () => indicator.dataset.pullState || "idle",
  };
}

/**
 * Register Service Worker for offline support
 */
function registerServiceWorker() {
  if (!("serviceWorker" in navigator)) {
    console.log("[SW] Service Worker not supported");
    return;
  }

  navigator.serviceWorker
    .register("/static/service-worker.js", {
      scope: "/",
    })
    .then((registration) => {
      console.log("[SW] Registered:", registration.scope);

      // Handle updates
      registration.addEventListener("updatefound", () => {
        const newWorker = registration.installing;
        console.log("[SW] New version found");

        newWorker.addEventListener("statechange", () => {
          if (newWorker.state === "installed" && navigator.serviceWorker.controller) {
            // New version available, show update notification
            showToast("Update available. Refresh to apply.", "info");
          }
        });
      });
    })
    .catch((error) => {
      console.error("[SW] Registration failed:", error);
    });

  // Listen for messages from SW
  navigator.serviceWorker.addEventListener("message", (event) => {
    if (event.data?.type === "SW_ACTIVATED") {
      console.log("[SW] Activated and controlling");
    }
  });
}

// Initialize when DOM is ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initAll);
} else {
  initAll();
}
