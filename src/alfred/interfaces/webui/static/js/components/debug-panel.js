/**
 * Debug Panel Component - Interactive diagnostics overlay
 *
 * Usage:
 * <debug-panel></debug-panel>
 *
 * Features:
 * - Tabbed interface (Messages, WebSocket, Session, DOM)
 * - Real-time updates
 * - Expandable/collapsible sections
 * - JSON tree viewer
 * - Search/filter capabilities
 */

class DebugPanel extends HTMLElement {
  constructor() {
    super();
    this._isOpen = false;
    this._activeTab = 'messages';
    this._data = {
      messages: [],
      websocket: {},
      session: {},
      dom: {}
    };
  }

  static get observedAttributes() {
    return ['open'];
  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (name === 'open') {
      this._isOpen = newValue !== null;
      this._render();
    }
  }

  connectedCallback() {
    this._render();
    this._attachListeners();
  }

  _attachListeners() {
    // Close on escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this._isOpen) {
        this.close();
      }
    });

    // Close on backdrop click
    this.addEventListener('click', (e) => {
      if (e.target === this) {
        this.close();
      }
    });
  }

  open(data = {}) {
    this._data = { ...this._data, ...data };
    this._isOpen = true;
    this.setAttribute('open', '');
    this._render();
  }

  close() {
    this._isOpen = false;
    this.removeAttribute('open');
  }

  toggle() {
    if (this._isOpen) {
      this.close();
    } else {
      this.open();
    }
  }

  setTab(tab) {
    this._activeTab = tab;
    this._render();
  }

  updateData(key, value) {
    this._data[key] = value;
    if (this._isOpen) {
      this._render();
    }
  }

  _render() {
    if (!this._isOpen) {
      this.innerHTML = '';
      return;
    }

    this.innerHTML = `
      <div class="debug-panel-overlay">
        <div class="debug-panel">
          <div class="debug-panel-header">
            <h2>🔍 Debug Inspector</h2>
            <button class="debug-panel-close" aria-label="Close">×</button>
          </div>
          
          <div class="debug-panel-tabs">
            <button class="debug-tab ${this._activeTab === 'messages' ? 'active' : ''}" data-tab="messages">
              💬 Messages (${this._data.messages?.length || 0})
            </button>
            <button class="debug-tab ${this._activeTab === 'websocket' ? 'active' : ''}" data-tab="websocket">
              🔌 WebSocket
            </button>
            <button class="debug-tab ${this._activeTab === 'session' ? 'active' : ''}" data-tab="session">
              📁 Session
            </button>
            <button class="debug-tab ${this._activeTab === 'dom' ? 'active' : ''}" data-tab="dom">
              🌲 DOM
            </button>
          </div>
          
          <div class="debug-panel-content">
            ${this._renderTabContent()}
          </div>
          
          <div class="debug-panel-footer">
            <button class="debug-refresh">🔄 Refresh</button>
            <button class="debug-export">📋 Export JSON</button>
          </div>
        </div>
      </div>
    `;

    this._attachEventListeners();
  }

  _renderTabContent() {
    switch (this._activeTab) {
      case 'messages':
        return this._renderMessagesTab();
      case 'websocket':
        return this._renderWebSocketTab();
      case 'session':
        return this._renderSessionTab();
      case 'dom':
        return this._renderDOMTab();
      default:
        return '<div class="debug-empty">Select a tab</div>';
    }
  }

  _renderMessagesTab() {
    const messages = this._data.messages || [];
    
    return `
      <div class="debug-messages">
        <div class="debug-toolbar">
          <input type="text" class="debug-search" placeholder="Search messages..." />
          <label class="debug-filter">
            <input type="checkbox" checked /> Show system
          </label>
        </div>
        
        <div class="debug-message-list">
          ${messages.length === 0 ? 
            '<div class="debug-empty">No messages</div>' :
            messages.map((msg, idx) => this._renderMessageCard(msg, idx)).join('')
          }
        </div>
      </div>
    `;
  }

  _renderMessageCard(msg, idx) {
    const role = msg.role || 'unknown';
    const roleClass = `role-${role}`;
    const id = msg.id || `idx-${idx}`;
    const content = msg.content_preview || msg.content || '';
    const hasTools = msg.has_tool_calls ? '🔧' : '';
    
    return `
      <div class="debug-message-card ${roleClass}" data-index="${idx}">
        <div class="debug-message-header">
          <span class="debug-message-role">${role}</span>
          <span class="debug-message-id" title="${id}">${id.substring(0, 20)}...</span>
          <span class="debug-message-tools">${hasTools}</span>
          <button class="debug-message-expand">▼</button>
        </div>
        <div class="debug-message-preview">${this._escapeHtml(content)}</div>
        <div class="debug-message-details" style="display: none;">
          <pre>${JSON.stringify(msg, null, 2)}</pre>
        </div>
      </div>
    `;
  }

  _renderWebSocketTab() {
    const ws = this._data.websocket || {};
    
    return `
      <div class="debug-websocket">
        <div class="debug-stats-grid">
          <div class="debug-stat">
            <span class="debug-stat-label">Status</span>
            <span class="debug-stat-value ${ws.isConnected ? 'success' : 'error'}">
              ${ws.isConnected ? '🟢 Connected' : '🔴 Disconnected'}
            </span>
          </div>
          <div class="debug-stat">
            <span class="debug-stat-label">Active Connections</span>
            <span class="debug-stat-value">${ws.active_connections || 0}</span>
          </div>
          <div class="debug-stat">
            <span class="debug-stat-label">Reconnect Attempts</span>
            <span class="debug-stat-value">${ws.reconnect_attempts || 0}</span>
          </div>
          <div class="debug-stat">
            <span class="debug-stat-label">Message Queue</span>
            <span class="debug-stat-value">${ws.message_queue_length || 0}</span>
          </div>
        </div>
        
        <div class="debug-section">
          <h3>Connection Snapshot</h3>
          ${this._renderJSONTree(ws.snapshot || {})}
        </div>
      </div>
    `;
  }

  _renderSessionTab() {
    const session = this._data.session || {};
    
    return `
      <div class="debug-session">
        <div class="debug-stats-grid">
          <div class="debug-stat">
            <span class="debug-stat-label">Session ID</span>
            <span class="debug-stat-value code">${session.id || 'N/A'}</span>
          </div>
          <div class="debug-stat">
            <span class="debug-stat-label">Message Count</span>
            <span class="debug-stat-value">${session.message_count || 0}</span>
          </div>
          <div class="debug-stat">
            <span class="debug-stat-label">Has Messages</span>
            <span class="debug-stat-value">${session.has_messages ? 'Yes' : 'No'}</span>
          </div>
        </div>
        
        <div class="debug-section">
          <h3>Full Session Data</h3>
          ${this._renderJSONTree(session)}
        </div>
      </div>
    `;
  }

  _renderDOMTab() {
    const dom = this._data.dom || {};
    
    return `
      <div class="debug-dom">
        <div class="debug-stats-grid">
          <div class="debug-stat">
            <span class="debug-stat-label">chat-message elements</span>
            <span class="debug-stat-value">${dom.chat_message_count || 0}</span>
          </div>
          <div class="debug-stat">
            <span class="debug-stat-label">Current Assistant</span>
            <span class="debug-stat-value ${dom.has_current_assistant ? 'success' : ''}">
              ${dom.has_current_assistant ? 'Yes' : 'No'}
            </span>
          </div>
          <div class="debug-stat">
            <span class="debug-stat-label">Composer State</span>
            <span class="debug-stat-value">${dom.composer_state || 'idle'}</span>
          </div>
        </div>
        
        ${dom.current_assistant ? `
          <div class="debug-section">
            <h3>Current Assistant Message</h3>
            ${this._renderJSONTree(dom.current_assistant)}
          </div>
        ` : ''}
        
        <div class="debug-section">
          <h3>DOM Messages</h3>
          <div class="debug-dom-list">
            ${(dom.messages || []).map(m => `
              <div class="debug-dom-item">
                <span class="debug-dom-role">${m.role}</span>
                <span class="debug-dom-id">${m.id}</span>
                <span class="debug-dom-length">${m.content_length} chars</span>
              </div>
            `).join('')}
          </div>
        </div>
      </div>
    `;
  }

  _renderJSONTree(obj, key = '', level = 0) {
    if (obj === null) return '<span class="json-null">null</span>';
    if (typeof obj === 'undefined') return '<span class="json-undefined">undefined</span>';
    if (typeof obj === 'string') return `<span class="json-string">"${this._escapeHtml(obj.substring(0, 200))}${obj.length > 200 ? '...' : ''}"</span>`;
    if (typeof obj === 'number') return `<span class="json-number">${obj}</span>`;
    if (typeof obj === 'boolean') return `<span class="json-boolean">${obj}</span>`;
    
    if (Array.isArray(obj)) {
      if (obj.length === 0) return '<span class="json-array">[]</span>';
      return `
        <div class="json-tree" style="margin-left: ${level * 16}px">
          <span class="json-toggle">▼</span>
          <span class="json-array">[${obj.length}]</span>
          <div class="json-children">
            ${obj.map((item, i) => `
              <div class="json-item">
                <span class="json-key">${i}:</span>
                ${this._renderJSONTree(item, '', level + 1)}
              </div>
            `).join('')}
          </div>
        </div>
      `;
    }
    
    const keys = Object.keys(obj);
    if (keys.length === 0) return '<span class="json-object">{}</span>';
    return `
      <div class="json-tree" style="margin-left: ${level * 16}px">
        <span class="json-toggle">▼</span>
        <span class="json-object">{${keys.length}}</span>
        <div class="json-children">
          ${keys.map(k => `
            <div class="json-item">
              <span class="json-key">${k}:</span>
              ${this._renderJSONTree(obj[k], k, level + 1)}
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  _attachEventListeners() {
    // Close button
    this.querySelector('.debug-panel-close')?.addEventListener('click', () => this.close());
    
    // Tab switching
    this.querySelectorAll('.debug-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        this.setTab(tab.dataset.tab);
      });
    });
    
    // Message expand/collapse
    this.querySelectorAll('.debug-message-header').forEach(header => {
      header.addEventListener('click', () => {
        const card = header.closest('.debug-message-card');
        const details = card.querySelector('.debug-message-details');
        const expand = header.querySelector('.debug-message-expand');
        const isOpen = details.style.display !== 'none';
        details.style.display = isOpen ? 'none' : 'block';
        expand.textContent = isOpen ? '▼' : '▲';
      });
    });
    
    // JSON toggle
    this.querySelectorAll('.json-toggle').forEach(toggle => {
      toggle.addEventListener('click', () => {
        const tree = toggle.closest('.json-tree');
        const children = tree.querySelector('.json-children');
        const isOpen = children.style.display !== 'none';
        children.style.display = isOpen ? 'none' : 'block';
        toggle.textContent = isOpen ? '▶' : '▼';
      });
    });
    
    // Refresh button
    this.querySelector('.debug-refresh')?.addEventListener('click', () => {
      this.dispatchEvent(new CustomEvent('debug-refresh', { bubbles: true }));
    });
    
    // Export button
    this.querySelector('.debug-export')?.addEventListener('click', () => {
      const json = JSON.stringify(this._data, null, 2);
      navigator.clipboard.writeText(json);
      this.dispatchEvent(new CustomEvent('debug-export', { bubbles: true }));
    });
  }

  _escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}

customElements.define('debug-panel', DebugPanel);
