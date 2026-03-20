/**
 * Chat Message Web Component
 * 
 * Usage: <chat-message role="user" content="Hello"></chat-message>
 * 
 * Attributes:
 *   - role: 'user' | 'assistant' | 'system'
 *   - content: The message content
 *   - timestamp: Optional ISO timestamp
 */
class ChatMessage extends HTMLElement {
  constructor() {
    super();
    this._content = '';
    this._role = 'user';
    this._timestamp = null;
    this._reasoning = '';
    this._reasoningExpanded = false;
  }

  static get observedAttributes() {
    return ['role', 'content', 'timestamp'];
  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (oldValue === newValue) return;
    
    switch (name) {
      case 'role':
        this._role = newValue || 'user';
        break;
      case 'content':
        this._content = newValue || '';
        break;
      case 'timestamp':
        this._timestamp = newValue;
        break;
    }
    this._render();
  }

  connectedCallback() {
    this._render();
  }

  _render() {
    const roleClass = this._role.toLowerCase();
    const timeDisplay = this._timestamp
      ? new Date(this._timestamp).toLocaleTimeString()
      : '';

    const reasoningSection = this._reasoning
      ? `<div class="reasoning-section"><div class="reasoning-header" onclick="this.closest('chat-message')._toggleReasoning()"><span class="reasoning-toggle">${this._reasoningExpanded ? '▼' : '▶'}</span><span class="reasoning-label">Thinking</span></div><div class="reasoning-content" style="display: ${this._reasoningExpanded ? 'block' : 'none'}">${this._escapeHtml(this._reasoning)}</div></div>`
      : '';

    this.innerHTML = `
      <div class="message ${roleClass}">
        <div class="message-header">
          <span class="message-role">${this._escapeHtml(this._role)}</span>
          ${timeDisplay ? `<span class="message-time">${timeDisplay}</span>` : ''}
        </div>
        ${reasoningSection}
        <div class="message-content">${this._escapeHtml(this._content)}</div>
      </div>
    `;
  }

  _escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // Public API
  setContent(content) {
    this._content = content;
    this.setAttribute('content', content);
  }

  getContent() {
    return this._content;
  }

  setRole(role) {
    this._role = role;
    this.setAttribute('role', role);
  }

  getRole() {
    return this._role;
  }

  setReasoning(reasoning) {
    this._reasoning = reasoning;
    this._render();
  }

  getReasoning() {
    return this._reasoning;
  }

  appendContent(chunk) {
    this._content += chunk;
    // Only update the content div, don't re-render entire element (preserves children like tool-call)
    const contentDiv = this.querySelector('.message-content');
    if (contentDiv) {
      contentDiv.textContent += chunk;
    } else {
      this._render();
    }
  }

  appendReasoning(chunk) {
    this._reasoning += chunk;
    // Update reasoning display if it exists
    const reasoningContent = this.querySelector('.reasoning-content');
    const reasoningSection = this.querySelector('.reasoning-section');
    if (reasoningContent) {
      reasoningContent.textContent = this._reasoning.trim();
    } else if (reasoningSection) {
      // Section exists but content div missing, re-render
      this._render();
    } else {
      // No reasoning section yet, create it
      this._render();
      // Auto-expand first reasoning chunk
      this._reasoningExpanded = true;
      this._render();
    }
  }

  _toggleReasoning() {
    this._reasoningExpanded = !this._reasoningExpanded;
    const content = this.querySelector('.reasoning-content');
    const toggle = this.querySelector('.reasoning-toggle');
    if (content) {
      content.style.display = this._reasoningExpanded ? 'block' : 'none';
    }
    if (toggle) {
      toggle.textContent = this._reasoningExpanded ? '▼' : '▶';
    }
  }
}

// Register the custom element
customElements.define('chat-message', ChatMessage);
