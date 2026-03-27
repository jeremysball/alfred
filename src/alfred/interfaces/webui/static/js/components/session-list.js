/**
 * SessionList Component - Interactive session browser
 *
 * Displays sessions as clickable cards with formatted metadata.
 * Clicking a session resumes it.
 */
class SessionList extends HTMLElement {
  constructor() {
    super();
    this.sessions = [];
    this._loading = false;
  }

  static get observedAttributes() {
    return ['sessions', 'loading'];
  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (name === 'sessions' && newValue) {
      try {
        this.sessions = JSON.parse(newValue);
        this._loading = false;
        this.render();
      } catch (e) {
        console.error('Failed to parse sessions:', e);
      }
    } else if (name === 'loading') {
      this._loading = newValue !== null;
      this.render();
    }
  }

  connectedCallback() {
    this.render();
  }

  /**
   * Set loading state
   * @param {boolean} value - Whether to show loading skeleton
   */
  set loading(value) {
    this._loading = value;
    if (value) {
      this.setAttribute('loading', '');
    } else {
      this.removeAttribute('loading');
    }
    this.render();
  }

  get loading() {
    return this._loading;
  }

  /**
   * Format a timestamp into a readable relative time
   */
  formatRelativeTime(isoString) {
    if (!isoString) return 'Unknown';

    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now - date;
    const diffSecs = Math.floor(diffMs / 1000);
    const diffMins = Math.floor(diffSecs / 60);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffSecs < 60) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
    });
  }

  /**
   * Format full date for tooltip
   */
  formatFullDate(isoString) {
    if (!isoString) return 'Unknown';
    return new Date(isoString).toLocaleString();
  }

  /**
   * Truncate session ID for display
   */
  truncateId(id) {
    if (!id || id.length <= 12) return id;
    return `${id.substring(0, 8)}...${id.substring(id.length - 4)}`;
  }

  /**
   * Render skeleton loading state
   */
  renderSkeleton() {
    this.innerHTML = '';

    const header = document.createElement('div');
    header.className = 'session-list-header';
    header.innerHTML = `
      <h3>Recent Sessions</h3>
      <span class="session-count skeleton-count">...</span>
    `;

    const list = document.createElement('div');
    list.className = 'session-list-container skeleton-container';

    // Create 5 skeleton session items
    for (let i = 0; i < 5; i++) {
      const item = document.createElement('div');
      item.className = 'session-card skeleton-session-card';
      item.innerHTML = `
        <div class="session-card-header">
          <span class="skeleton skeleton--text" style="width: 120px; height: 16px;"></span>
          <span class="skeleton skeleton--text" style="width: 60px; height: 14px;"></span>
        </div>
        <div class="session-card-body">
          <span class="skeleton skeleton--text" style="width: 80px; height: 14px;"></span>
        </div>
      `;
      list.appendChild(item);
    }

    this.appendChild(header);
    this.appendChild(list);
  }

  /**
   * Render the session list
   */
  render() {
    // Show skeleton loading state
    if (this._loading) {
      this.renderSkeleton();
      return;
    }

    if (!this.sessions || this.sessions.length === 0) {
      this.innerHTML = `
        <div class="session-list-empty">
          <span class="session-list-icon">📂</span>
          <p>No sessions found</p>
        </div>
      `;
      return;
    }

    const header = document.createElement('div');
    header.className = 'session-list-header';
    header.innerHTML = `
      <h3>Recent Sessions</h3>
      <span class="session-count">${this.sessions.length}</span>
    `;

    const list = document.createElement('div');
    list.className = 'session-list-container';

    this.sessions.forEach((session, index) => {
      const card = document.createElement('div');
      card.className = 'session-card';
      card.setAttribute('data-session-id', session.id);
      card.setAttribute('role', 'button');
      card.setAttribute('tabindex', '0');
      card.title = `Click to resume session ${session.id}`;

      const relativeTime = this.formatRelativeTime(session.lastActive || session.created);
      const fullDate = this.formatFullDate(session.lastActive || session.created);
      const displayId = this.truncateId(session.id);
      const messageCount = session.messageCount || 0;

      card.innerHTML = `
        <div class="session-card-header">
          <span class="session-id" title="${session.id}">${displayId}</span>
          <span class="session-time" title="${fullDate}">${relativeTime}</span>
        </div>
        <div class="session-card-body">
          <span class="session-messages">
            <span class="message-icon">💬</span>
            ${messageCount} message${messageCount !== 1 ? 's' : ''}
          </span>
        </div>
        <div class="session-card-footer">
          <span class="session-action">Click to resume →</span>
        </div>
      `;

      // Click handler
      card.addEventListener('click', () => {
        this.handleSessionClick(session.id);
      });

      // Keyboard handler for accessibility
      card.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          this.handleSessionClick(session.id);
        }
      });

      // Staggered animation delay
      card.style.animationDelay = `${index * 50}ms`;

      list.appendChild(card);
    });

    this.innerHTML = '';
    this.appendChild(header);
    this.appendChild(list);
  }

  /**
   * Handle session card click - dispatch event to resume session
   */
  handleSessionClick(sessionId) {
    this.dispatchEvent(new CustomEvent('session-select', {
      detail: { sessionId },
      bubbles: true,
      composed: true,
    }));
  }
}

// Register the custom element
customElements.define('session-list', SessionList);
