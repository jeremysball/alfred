/**
 * OfflineIndicator - Custom element showing connection status
 *
 * Usage:
 * <offline-indicator id="offline-indicator" state="online"></offline-indicator>
 *
 * States:
 *   - 'online': Hidden
 *   - 'offline': Shows red banner with offline message
 *   - 'reconnecting': Shows amber banner with spinner
 */
export class OfflineIndicator extends HTMLElement {
  constructor() {
    super();
    this._state = "online";
  }

  static get observedAttributes() {
    return ["state"];
  }

  attributeChangedCallback(name, _oldValue, newValue) {
    if (name === "state" && newValue) {
      this._state = newValue;
      this.render();
    }
  }

  connectedCallback() {
    this.render();
  }

  /**
   * Set the indicator state
   * @param {string} state - 'online', 'offline', or 'reconnecting'
   */
  setState(state) {
    this.setAttribute("state", state);
  }

  /**
   * Render the indicator based on current state
   */
  render() {
    // Clear existing content
    this.innerHTML = "";

    // Online state: don't show anything
    if (this._state === "online") {
      this.style.display = "none";
      return;
    }

    // Show indicator for offline/reconnecting
    this.style.display = "block";

    const isReconnecting = this._state === "reconnecting";
    const icon = isReconnecting ? "⟳" : "⚠";
    const message = isReconnecting ? "Reconnecting..." : "You are offline";
    const subMessage = isReconnecting
      ? "Attempting to reconnect to server"
      : "Some features may be unavailable";

    this.innerHTML = `
      <div class="offline-indicator ${this._state}">
        <div class="offline-indicator__content">
          <span class="offline-indicator__icon ${isReconnecting ? "spinning" : ""}">${icon}</span>
          <div class="offline-indicator__text">
            <span class="offline-indicator__message">${message}</span>
            <span class="offline-indicator__sub">${subMessage}</span>
          </div>
          ${
            !isReconnecting
              ? `
            <button class="offline-indicator__retry" type="button">
              Retry
            </button>
          `
              : ""
          }
        </div>
      </div>
    `;

    // Add event listener to retry button
    const retryButton = this.querySelector(".offline-indicator__retry");
    if (retryButton) {
      retryButton.addEventListener("click", () => this.handleRetry());
    }
  }

  /**
   * Handle retry button click
   */
  handleRetry() {
    // Trigger page reload to re-establish connections
    window.location.reload();
  }
}

// Register the custom element
customElements.define("offline-indicator", OfflineIndicator);
