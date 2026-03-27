/**
 * ConnectionMonitor - Track WebSocket and online/offline state
 *
 * Emits events:
 *   - 'statechange': { state: string, previousState: string }
 *
 * States:
 *   - 'online': Connected to server
 *   - 'offline': Disconnected from server
 *   - 'reconnecting': Attempting to reconnect
 */
export class ConnectionMonitor extends EventTarget {
  constructor() {
    super();
    this.state = 'online';
    this.previousState = 'online';
    this.wsClient = null;

    // Listen to browser online/offline events
    window.addEventListener('online', () => this.handleBrowserOnline());
    window.addEventListener('offline', () => this.handleBrowserOffline());
  }

  /**
   * Track a WebSocket client
   * @param {WebSocketClient} wsClient - The WebSocket client to monitor
   */
  trackWebSocket(wsClient) {
    this.wsClient = wsClient;

    // Listen to WebSocket events (AlfredWebSocketClient events)
    wsClient.addEventListener('connected', () => this.handleWsConnected());
    wsClient.addEventListener('disconnected', () => this.handleWsDisconnected());
    wsClient.addEventListener('error', () => this.handleWsError());

    // Set initial state based on current connection
    if (wsClient.isConnected) {
      this.setState('online');
    } else {
      this.setState('offline');
    }
  }

  /**
   * Handle WebSocket connected
   */
  handleWsConnected() {
    this.setState('online');
  }

  /**
   * Handle WebSocket disconnected
   */
  handleWsDisconnected() {
    const snapshot = this.wsClient?.getConnectionSnapshot();
    const isReconnecting = snapshot?.reconnectAttempts > 0;

    if (isReconnecting) {
      this.setState('reconnecting');
    } else {
      this.setState('offline');
    }
  }

  /**
   * Handle WebSocket error
   */
  handleWsError() {
    const snapshot = this.wsClient?.getConnectionSnapshot();
    const isReconnecting = snapshot?.reconnectAttempts > 0;

    if (isReconnecting) {
      this.setState('reconnecting');
    } else {
      this.setState('offline');
    }
  }

  /**
   * Handle browser online event
   */
  handleBrowserOnline() {
    console.log('[Connection] Browser reports online');
    // WebSocket client handles reconnection automatically
    // We just update our state based on its reconnect attempts
    const snapshot = this.wsClient?.getConnectionSnapshot();
    if (snapshot?.reconnectAttempts > 0 && !this.wsClient?.isConnected) {
      this.setState('reconnecting');
    }
  }

  /**
   * Handle browser offline event
   */
  handleBrowserOffline() {
    console.log('[Connection] Browser reports offline');
    this.setState('offline');
  }

  /**
   * Set the connection state and emit event
   * @param {string} newState - New state ('online', 'offline', 'reconnecting')
   */
  setState(newState) {
    if (this.state === newState) return;

    this.previousState = this.state;
    this.state = newState;

    this.dispatchEvent(new CustomEvent('statechange', {
      detail: {
        state: this.state,
        previousState: this.previousState
      }
    }));
  }

  /**
   * Get current state
   * @returns {string} Current state
   */
  getState() {
    return this.state;
  }

  /**
   * Check if currently online
   * @returns {boolean} True if online
   */
  isOnline() {
    return this.state === 'online';
  }
}
