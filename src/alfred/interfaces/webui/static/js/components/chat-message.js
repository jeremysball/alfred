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

    this.innerHTML = `
      <div class="message ${roleClass}">
        <div class="message-header">
          <span class="message-role">${this._escapeHtml(this._role)}</span>
          ${timeDisplay ? `<span class="message-time">${timeDisplay}</span>` : ''}
        </div>
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
}

// Register the custom element
customElements.define('chat-message', ChatMessage);
