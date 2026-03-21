/**
 * WebSocket Client for Alfred Web UI
 * 
 * Manages WebSocket connection, message handling, and reconnection logic.
 * Includes keepalive ping/pong and visibility handling for mobile browser switching.
 */
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
  }

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected');
      return;
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
        // Handle pong responses
        if (message.type === 'pong') {
          this._clearPingTimeout();
          return;
        }
        console.log('WebSocket message received:', message);
        this.dispatchEvent(new CustomEvent('message', { detail: message }));
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
        this.dispatchEvent(new CustomEvent('error', { detail: error }));
      }
    };

    this.ws.onclose = (event) => {
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
      this.ws.send(message);
    }
  }
}

// Export for module usage if supported
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { AlfredWebSocketClient };
}
