/**
 * WebSocket Client for Alfred Web UI
 * 
 * Manages WebSocket connection, message handling, and reconnection logic.
 */
class AlfredWebSocketClient extends EventTarget {
  constructor(url = null) {
    super();
    this.url = url || `ws://${window.location.host}/ws`;
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000;
    this.isConnected = false;
    this.messageQueue = [];
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
      this._flushMessageQueue();
      this.dispatchEvent(new CustomEvent('connected', { detail: event }));
    };

    this.ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
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
      this.dispatchEvent(new CustomEvent('disconnected', { detail: event }));
      
      if (!event.wasClean && this.reconnectAttempts < this.maxReconnectAttempts) {
        this._scheduleReconnect();
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      this.dispatchEvent(new CustomEvent('error', { detail: error }));
    };
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
