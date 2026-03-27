/**
 * WebSocket Client for Alfred Web UI
 * 
 * Manages WebSocket connection, message handling, and reconnection logic.
 * Includes keepalive ping/pong and visibility handling for mobile browser switching.
 */
const ALFRED_WEBUI_CONFIG = window.__ALFRED_WEBUI_CONFIG__ ?? { debug: false };
const WEBSOCKET_DEBUG_ENABLED = Boolean(ALFRED_WEBUI_CONFIG.debug);

class WebSocketDebugStats {
  constructor() {
    this.incomingCounts = new Map();
    this.outgoingCounts = new Map();
    this.totalBytesReceived = 0;
    this.totalBytesSent = 0;
    this.maxIncomingBytes = 0;
    this.maxOutgoingBytes = 0;
    this.maxIncomingType = '';
    this.maxOutgoingType = '';
    this.lastIncomingType = '';
    this.lastOutgoingType = '';
    this.closeCode = null;
    this.closeReason = '';
    this.wasClean = null;
  }

  _byteLength(text) {
    return new TextEncoder().encode(text).length;
  }

  _increment(counts, key) {
    counts.set(key, (counts.get(key) || 0) + 1);
  }

  recordIncoming(messageType, rawText) {
    const type = messageType || 'unknown';
    const bytes = this._byteLength(rawText);
    this._increment(this.incomingCounts, type);
    this.totalBytesReceived += bytes;
    this.lastIncomingType = type;
    if (bytes > this.maxIncomingBytes) {
      this.maxIncomingBytes = bytes;
      this.maxIncomingType = type;
    }
  }

  recordOutgoing(messageType, rawText) {
    const type = messageType || 'unknown';
    const bytes = this._byteLength(rawText);
    this._increment(this.outgoingCounts, type);
    this.totalBytesSent += bytes;
    this.lastOutgoingType = type;
    if (bytes > this.maxOutgoingBytes) {
      this.maxOutgoingBytes = bytes;
      this.maxOutgoingType = type;
    }
  }

  recordClose(event) {
    this.closeCode = event.code;
    this.closeReason = event.reason || '';
    this.wasClean = event.wasClean;
  }

  _countsToObject(counts) {
    return Object.fromEntries([...counts.entries()].sort(([a], [b]) => a.localeCompare(b)));
  }

  summary() {
    return {
      closeCode: this.closeCode,
      closeReason: this.closeReason,
      wasClean: this.wasClean,
      lastIncomingType: this.lastIncomingType,
      lastOutgoingType: this.lastOutgoingType,
      incomingCounts: this._countsToObject(this.incomingCounts),
      outgoingCounts: this._countsToObject(this.outgoingCounts),
      totalBytesReceived: this.totalBytesReceived,
      totalBytesSent: this.totalBytesSent,
      maxIncomingBytes: this.maxIncomingBytes,
      maxOutgoingBytes: this.maxOutgoingBytes,
      maxIncomingType: this.maxIncomingType,
      maxOutgoingType: this.maxOutgoingType,
    };
  }
}

class AlfredWebSocketClient extends EventTarget {
  constructor(url = null) {
    super();
    const { protocol, host } = window.location;
    const scheme = protocol === 'https:' ? 'wss' : 'ws';
    this.url = url || `${scheme}://${host}/ws`;
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 10; // Increased for mobile
    this.reconnectDelay = 1000;
    this.isConnected = false;
    this.messageQueue = [];
    this.pingInterval = null;
    this.pingTimeout = null;
    this.visibilityHandler = null;
    this.debugEnabled = WEBSOCKET_DEBUG_ENABLED;
    this.debugStats = this.debugEnabled ? new WebSocketDebugStats() : null;
    this.lastPingAt = null;
    this.lastPongAt = null;
    this.lastPingLatencyMs = null;
    this.lastCloseAt = null;
    this.lastCloseCode = null;
    this.lastCloseReason = '';
    this.lastCloseWasClean = null;
    this._pendingManualReconnect = false;
    // Lifecycle handler tracking to prevent duplicate listeners on reconnect
    this._freezeHandler = null;
    this._resumeHandler = null;
    this._pagehideHandler = null;
    this._pageshowHandler = null;
  }

  connect() {
    // Idempotent connect: guard against all active states
    if (this.ws?.readyState === WebSocket.OPEN) {
      if (this.debugEnabled) {
        console.log('[websocket] Already connected');
      }
      return;
    }

    if (this.ws?.readyState === WebSocket.CONNECTING) {
      if (this.debugEnabled) {
        console.log('[websocket] Connection in progress');
      }
      return;
    }

    if (this.ws?.readyState === WebSocket.CLOSING) {
      if (this.debugEnabled) {
        console.log('[websocket] Closing, will reconnect when closed');
      }
      return;
    }

    if (this.debugEnabled) {
      this.debugStats = new WebSocketDebugStats();
    }

    if (this.debugEnabled) {
      console.log('[websocket] Connecting to:', this.url);
    }
    this.ws = new WebSocket(this.url);

    this.ws.onopen = (event) => {
      if (this.debugEnabled) {
        console.log('[websocket] WebSocket connected');
      }
      this.isConnected = true;
      this.reconnectAttempts = 0;
      this._startPing();
      this._flushMessageQueue();
      this.dispatchEvent(new CustomEvent('connected', { detail: event }));
    };

    this.ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        if (this.debugStats) {
          this.debugStats.recordIncoming(message.type || 'unknown', event.data);
        }
        // Handle pong responses
        if (message.type === 'pong') {
          this.lastPongAt = Date.now();
          if (this.lastPingAt !== null) {
            this.lastPingLatencyMs = this.lastPongAt - this.lastPingAt;
          }
          if (this.debugEnabled) {
            console.log(`[websocket] Pong received, latency: ${this.lastPingLatencyMs}ms`);
          }
          this._clearPingTimeout();
          return;
        }
        this.dispatchEvent(new CustomEvent('message', { detail: message }));
      } catch (error) {
        if (this.debugStats) {
          this.debugStats.recordIncoming('parse_error', String(event.data));
        }
        console.error('Failed to parse WebSocket message:', error);
        this.dispatchEvent(new CustomEvent('error', { detail: error }));
      }
    };

    this.ws.onclose = (event) => {
      if (this.debugStats) {
        this.debugStats.recordClose(event);
      }
      if (this.debugEnabled) {
        console.log(`[websocket] WebSocket closed: code=${event.code}, reason="${event.reason || ''}", clean=${event.wasClean}`);
      }
      this.isConnected = false;
      this.lastCloseAt = Date.now();
      this.lastCloseCode = event.code;
      this.lastCloseReason = event.reason || '';
      this.lastCloseWasClean = event.wasClean;
      this._stopPing();
      this.dispatchEvent(new CustomEvent('disconnected', { detail: event }));
      
      if (this._pendingManualReconnect) {
        this._pendingManualReconnect = false;
        this.connect();
        return;
      }

      // Always try to reconnect unless explicitly disconnected
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        this._scheduleReconnect();
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      this.dispatchEvent(new CustomEvent('error', { detail: error }));
    };

    // Setup visibility handling for mobile browser switching
    this._setupVisibilityHandling();
  }

  _setupVisibilityHandling() {
    // Clean up existing listeners to prevent duplicates on reconnect
    if (this.visibilityHandler) {
      document.removeEventListener('visibilitychange', this.visibilityHandler);
    }
    if (this._freezeHandler) {
      document.removeEventListener('freeze', this._freezeHandler);
    }
    if (this._resumeHandler) {
      document.removeEventListener('resume', this._resumeHandler);
    }
    if (this._pagehideHandler) {
      window.removeEventListener('pagehide', this._pagehideHandler);
    }
    if (this._pageshowHandler) {
      window.removeEventListener('pageshow', this._pageshowHandler);
    }

    this.visibilityHandler = () => {
      const isVisible = document.visibilityState === 'visible';

      // Send visibility state to server
      this.send({
        type: 'client.visibility',
        payload: {
          isVisible: isVisible,
          timestamp: Date.now()
        }
      });

      if (isVisible) {
        if (this.debugEnabled) {
          console.log('[websocket] Page visible, checking connection');
        }
        if (!this.isConnected || this.ws?.readyState !== WebSocket.OPEN) {
          if (this.debugEnabled) {
            console.log('[websocket] Reconnecting on visibility change');
          }
          this.reconnectAttempts = 0; // Reset for user-initiated reconnect
          this.connect();
        }
      } else {
        // Page hidden - send immediate ping to keep connection alive longer
        // Mobile OS gives us a small window before throttling
        this._sendKeepalive();
      }
    };

    document.addEventListener('visibilitychange', this.visibilityHandler);

    // Page Lifecycle API for more granular control (Chrome/Android)
    if ('onfreeze' in document) {
      this._freezeHandler = () => {
        if (this.debugEnabled) {
          console.log('[websocket] Page frozen by OS');
        }
        this._stopPing();
      };
      this._resumeHandler = () => {
        if (this.debugEnabled) {
          console.log('[websocket] Page resumed from frozen state');
        }
        this.reconnectAttempts = 0;
        this.connect();
      };
      document.addEventListener('freeze', this._freezeHandler);
      document.addEventListener('resume', this._resumeHandler);
    }

    // Handle pagehide/pageshow for iOS Safari
    this._pagehideHandler = (e) => {
      if (e.persisted) {
        // Page is going into bfcache - connection will be suspended
        if (this.debugEnabled) {
          console.log('[websocket] Page entering bfcache');
        }
        this._stopPing();
      }
    };
    this._pageshowHandler = (e) => {
      if (e.persisted) {
        // Page restored from bfcache - connection is dead, reconnect
        if (this.debugEnabled) {
          console.log('[websocket] Page restored from bfcache, reconnecting');
        }
        this.reconnectAttempts = 0;
        this.connect();
      }
    };
    window.addEventListener('pagehide', this._pagehideHandler);
    window.addEventListener('pageshow', this._pageshowHandler);
  }

  _sendKeepalive() {
    // Send immediate ping when page is being hidden
    // This may keep the connection alive a bit longer on some mobile browsers
    if (this.ws?.readyState === WebSocket.OPEN) {
      try {
        const pingMessage = JSON.stringify({ type: 'ping', ts: Date.now() });
        this.ws.send(pingMessage);
        if (this.debugStats) {
          this.debugStats.recordOutgoing('ping', pingMessage);
        }
      } catch (e) {
        // Ignore errors on hidden page
      }
    }
  }

  _startPing() {
    // Aggressive keepalive to prevent disconnection on mobile networks
    const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
    const pingIntervalMs = isMobile ? 3000 : 5000;
    const pongTimeoutMs = isMobile ? 2000 : 3000;
    
    this.pingInterval = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        const pingMessage = JSON.stringify({ type: 'ping' });
        this.lastPingAt = Date.now();
        this.ws.send(pingMessage);
        if (this.debugStats) {
          this.debugStats.recordOutgoing('ping', pingMessage);
        }
        // Expect pong within timeout window
        this.pingTimeout = setTimeout(() => {
          if (this.debugEnabled) {
            console.log('[websocket] Ping timeout, closing connection');
          }
          this.ws?.close();
        }, pongTimeoutMs);
      }
    }, pingIntervalMs);
    
    // Listen for online/offline events
    this._onlineHandler = () => {
      if (this.debugEnabled) {
        console.log('[websocket] Network online');
      }
      if (!this.isConnected) {
        this.reconnectAttempts = 0;
        this.connect();
      }
    };
    this._offlineHandler = () => {
      if (this.debugEnabled) {
        console.log('[websocket] Network offline');
      }
      this._stopPing();
    };
    window.addEventListener('online', this._onlineHandler);
    window.addEventListener('offline', this._offlineHandler);
  }

  _clearPingTimeout() {
    if (this.pingTimeout) {
      clearTimeout(this.pingTimeout);
      this.pingTimeout = null;
    }
  }

  _stopPing() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
    this._clearPingTimeout();
    if (this._onlineHandler) {
      window.removeEventListener('online', this._onlineHandler);
      this._onlineHandler = null;
    }
    if (this._offlineHandler) {
      window.removeEventListener('offline', this._offlineHandler);
      this._offlineHandler = null;
    }
  }

  disconnect() {
    // Clean up all event listeners
    if (this.visibilityHandler) {
      document.removeEventListener('visibilitychange', this.visibilityHandler);
      this.visibilityHandler = null;
    }
    this._stopPing();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
      this.isConnected = false;
    }
  }

  reconnect() {
    this._pendingManualReconnect = true;
    this.reconnectAttempts = 0;

    if (!this.ws || this.ws.readyState === WebSocket.CLOSED) {
      this._pendingManualReconnect = false;
      this.connect();
      return;
    }

    this.ws.close();
  }

  send(message) {
    const messageStr = typeof message === 'string' ? message : JSON.stringify(message);

    if (this.isConnected && this.ws?.readyState === WebSocket.OPEN) {
      if (this.debugStats) {
        this.debugStats.recordOutgoing(this._getMessageType(messageStr, message), messageStr);
      }
      this.ws.send(messageStr);
    } else {
      if (this.debugEnabled) {
        console.log('[websocket] Queueing message until connection is ready');
      }
      this.messageQueue.push(messageStr);
    }
  }

  sendChat(message, sessionId = null) {
    const payload = {
      type: 'chat.send',
      payload: {
        content: message
      }
    };
    if (sessionId) {
      payload.payload.session_id = sessionId;
    }
    this.send(payload);
  }

  sendCancel() {
    this.send({
      type: 'chat.cancel'
    });
  }

  sendChatEdit(messageId, content) {
    this.send({
      type: 'chat.edit',
      payload: {
        messageId,
        content,
      }
    });
  }

  sendCommand(command) {
    if (this.debugEnabled) {
      console.log('[websocket] Sending command:', command);
    }
    this.send({
      type: 'command.execute',
      payload: {
        command: command
      }
    });
  }

  sendAck(messageId) {
    this.send({
      type: 'ack',
      ref_id: messageId
    });
  }

  getConnectionSnapshot() {
    const readyState = this.ws?.readyState;
    let connectionState = 'disconnected';

    if (this.isConnected && readyState === WebSocket.OPEN) {
      connectionState = 'connected';
    } else if (readyState === WebSocket.CONNECTING) {
      connectionState = 'connecting';
    } else if (this.reconnectAttempts > 0) {
      connectionState = 'reconnecting';
    }

    return {
      url: this.url,
      isConnected: this.isConnected,
      readyState,
      connectionState,
      reconnectAttempts: this.reconnectAttempts,
      maxReconnectAttempts: this.maxReconnectAttempts,
      pingIntervalActive: this.pingInterval !== null,
      pingTimeoutActive: this.pingTimeout !== null,
      lastPingAt: this.lastPingAt,
      lastPongAt: this.lastPongAt,
      lastPingLatencyMs: this.lastPingLatencyMs,
      lastCloseAt: this.lastCloseAt,
      lastCloseCode: this.lastCloseCode,
      lastCloseReason: this.lastCloseReason,
      lastCloseWasClean: this.lastCloseWasClean,
      debugEnabled: this.debugEnabled,
      debugSummary: this.debugStats ? this.debugStats.summary() : null,
    };
  }

  _getMessageType(messageStr, originalMessage = null) {
    if (originalMessage && typeof originalMessage !== 'string' && originalMessage.type) {
      return originalMessage.type;
    }

    try {
      const parsed = JSON.parse(messageStr);
      return parsed.type || 'unknown';
    } catch {
      return typeof originalMessage === 'string' ? 'text' : 'unknown';
    }
  }

  _scheduleReconnect() {
    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    if (this.debugEnabled) {
      console.log(`[websocket] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
    }

    setTimeout(() => {
      this.connect();
    }, delay);
  }

  _flushMessageQueue() {
    const count = this.messageQueue.length;
    if (this.debugEnabled && count > 0) {
      console.log(`[websocket] Flushing ${count} queued message(s)`);
    }
    while (this.messageQueue.length > 0) {
      const message = this.messageQueue.shift();
      if (this.debugStats) {
        this.debugStats.recordOutgoing(this._getMessageType(message), message);
      }
      this.ws.send(message);
    }
  }
}

// Export for ESM and browser usage
export { AlfredWebSocketClient };

if (typeof window !== 'undefined') {
  window.AlfredWebSocketClient = AlfredWebSocketClient;
}
