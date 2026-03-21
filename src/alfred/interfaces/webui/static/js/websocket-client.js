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
    this.url = url || `ws://${window.location.host}/ws`;
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
  }

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected');
      return;
    }

    if (this.debugEnabled) {
      this.debugStats = new WebSocketDebugStats();
    }

    console.log('Connecting to WebSocket:', this.url);
    this.ws = new WebSocket(this.url);

    this.ws.onopen = (event) => {
      console.log('WebSocket connected');
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
        console.info('[WebSocket debug] close summary', this.debugStats.summary());
      }
      console.log('WebSocket closed:', event.code, event.reason);
      this.isConnected = false;
      this._stopPing();
      this.dispatchEvent(new CustomEvent('disconnected', { detail: event }));
      
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
    if (this.visibilityHandler) {
      document.removeEventListener('visibilitychange', this.visibilityHandler);
    }
    
    this.visibilityHandler = () => {
      if (document.visibilityState === 'visible') {
        console.log('Page visible, checking WebSocket connection');
        if (!this.isConnected || this.ws?.readyState !== WebSocket.OPEN) {
          console.log('Reconnecting on visibility change');
          this.reconnectAttempts = 0; // Reset for user-initiated reconnect
          this.connect();
        }
      }
    };
    
    document.addEventListener('visibilitychange', this.visibilityHandler);
  }

  _startPing() {
    // Send ping every 15 seconds to keep connection alive
    this.pingInterval = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'ping' }));
        if (this.debugStats) {
          this.debugStats.recordOutgoing('ping', JSON.stringify({ type: 'ping' }));
        }
        // Expect pong within 5 seconds
        this.pingTimeout = setTimeout(() => {
          console.log('Ping timeout, closing connection');
          this.ws?.close();
        }, 5000);
      }
    }, 15000);
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
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
      this.isConnected = false;
    }
  }

  send(message) {
    const messageStr = typeof message === 'string' ? message : JSON.stringify(message);

    if (this.isConnected && this.ws?.readyState === WebSocket.OPEN) {
      if (this.debugStats) {
        this.debugStats.recordOutgoing(this._getMessageType(messageStr, message), messageStr);
      }
      this.ws.send(messageStr);
    } else {
      console.log('Queueing message until connection is ready');
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

  sendCommand(command) {
    console.log('[WebSocket] Sending command:', command);
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
    console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
    
    setTimeout(() => {
      this.connect();
    }, delay);
  }

  _flushMessageQueue() {
    while (this.messageQueue.length > 0) {
      const message = this.messageQueue.shift();
      if (this.debugStats) {
        this.debugStats.recordOutgoing(this._getMessageType(message), message);
      }
      this.ws.send(message);
    }
  }
}

// Export for module usage if supported
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { AlfredWebSocketClient };
}
