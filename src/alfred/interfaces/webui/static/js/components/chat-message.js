/**
 * Chat Message Web Component
 * 
 * Usage: <chat-message role="user" content="Hello"></chat-message>
 * 
 * Attributes:
 *   - role: 'user' | 'assistant' | 'system'
 *   - content: The message content
 *   - timestamp: Optional ISO timestamp
 *   - message-id: Optional message ID for actions
 */
class ChatMessage extends HTMLElement {
  constructor() {
    super();
    this._content = '';
    this._role = 'user';
    this._timestamp = null;
    this._reasoning = '';
    this._reasoningExpanded = false;
    this._messageId = null;
    this._copied = false;
  }

  static get observedAttributes() {
    return ['role', 'content', 'timestamp', 'message-id'];
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
      case 'message-id':
        this._messageId = newValue;
        break;
    }
    this._render();
  }

  connectedCallback() {
    this._render();
    this._applySyntaxHighlighting();
    this._setupEventListeners();
  }

  _getAvatar() {
    switch (this._role) {
      case 'user':
        return '●'; // Solid circle for user
      case 'assistant':
        return '◆'; // Diamond for assistant
      case 'system':
        return '▸'; // Arrow for system
      default:
        return '○'; // Empty circle default
    }
  }

  _getDisplayName() {
    switch (this._role) {
      case 'assistant':
        return 'Alfred';
      case 'user':
        return 'You';
      case 'system':
        return 'System';
      default:
        return this._role;
    }
  }

  _formatTime() {
    if (!this._timestamp) return '';
    const date = new Date(this._timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  _render() {
    const roleClass = this._role.toLowerCase();
    const avatar = this._getAvatar();
    const displayName = this._getDisplayName();
    const timeDisplay = this._formatTime();

    // System messages are simpler
    if (this._role === 'system') {
      this.innerHTML = `
        <div class="message ${roleClass}">
          <div class="message-bubble">
            <span class="message-avatar-small">${avatar}</span>
            <span class="message-content">${this._escapeHtml(this._content)}</span>
          </div>
        </div>
      `;
      return;
    }

    // Build reasoning section if present
    const reasoningSection = this._reasoning
      ? `<div class="reasoning-section">
          <div class="reasoning-header" onclick="this.closest('chat-message')._toggleReasoning()">
            <span class="reasoning-icon">◈</span>
            <span class="reasoning-label">Thinking</span>
            <span class="reasoning-toggle">${this._reasoningExpanded ? '−' : '+'}</span>
          </div>
          <div class="reasoning-content" style="display: ${this._reasoningExpanded ? 'block' : 'none'}">
            ${this._escapeHtml(this._reasoning)}
          </div>
        </div>`
      : '';

    // Build action buttons (only for assistant messages)
    const actionButtons = this._role === 'assistant' 
      ? `<div class="message-actions">
          <button class="message-action" data-action="copy" title="Copy message">
            <span class="action-icon">□</span>
            <span class="action-text">Copy</span>
          </button>
          <button class="message-action" data-action="retry" title="Regenerate response">
            <span class="action-icon">↻</span>
            <span class="action-text">Retry</span>
          </button>
          <div class="message-actions-spacer"></div>
          <button class="message-action feedback-btn" data-action="thumbs-up" title="Helpful">
            <span class="action-icon">+</span>
          </button>
          <button class="message-action feedback-btn" data-action="thumbs-down" title="Not helpful">
            <span class="action-icon">−</span>
          </button>
        </div>`
      : '';

    // Render content: markdown for assistant, plain text for user
    const renderedContent = this._role === 'assistant'
      ? this._renderMarkdown(this._content)
      : this._escapeHtml(this._content);

    this.innerHTML = `
      <div class="message ${roleClass}">
        <div class="message-header">
          <span class="message-avatar" aria-hidden="true">${avatar}</span>
          <span class="message-role">${displayName}</span>
          ${timeDisplay ? `<span class="message-time">${timeDisplay}</span>` : ''}
        </div>
        ${reasoningSection}
        <div class="message-bubble">
          <div class="message-content">${renderedContent}</div>
        </div>
        ${actionButtons}
      </div>
    `;
  }

  _renderMarkdown(content) {
    // Check if marked is available
    if (typeof marked === 'undefined') {
      console.warn('marked.js not loaded, falling back to plain text');
      return this._escapeHtml(content);
    }

    // Configure marked options
    marked.setOptions({
      gfm: true,              // GitHub Flavored Markdown (tables, etc.)
      breaks: true,           // Convert line breaks to <br>
      headerIds: false,       // Don't add ids to headers
      mangle: false,          // Don't mangle email addresses
    });

    // Parse markdown
    const html = marked.parse(content);

    return html;
  }

  _applySyntaxHighlighting() {
    // Check if highlight.js is available
    if (typeof hljs === 'undefined') {
      console.warn('highlight.js not loaded, skipping syntax highlighting');
      return;
    }

    // Find all code blocks and apply highlighting
    const codeBlocks = this.querySelectorAll('pre code');
    codeBlocks.forEach((block) => {
      hljs.highlightElement(block);
    });
  }

  _setupEventListeners() {
    // Copy button
    this.querySelector('[data-action="copy"]')?.addEventListener('click', () => {
      this._copyToClipboard();
    });

    // Retry button
    this.querySelector('[data-action="retry"]')?.addEventListener('click', () => {
      this._retryMessage();
    });

    // Feedback buttons
    this.querySelector('[data-action="thumbs-up"]')?.addEventListener('click', (e) => {
      this._sendFeedback('positive');
      e.currentTarget.classList.toggle('active');
    });

    this.querySelector('[data-action="thumbs-down"]')?.addEventListener('click', (e) => {
      this._sendFeedback('negative');
      e.currentTarget.classList.toggle('active');
    });
  }

  async _copyToClipboard() {
    try {
      await navigator.clipboard.writeText(this._content);
      const btn = this.querySelector('[data-action="copy"]');
      if (btn) {
        const originalText = btn.innerHTML;
        btn.innerHTML = `<span class="action-icon">✓</span><span class="action-text">Copied!</span>`;
        btn.classList.add('copied');
        setTimeout(() => {
          btn.innerHTML = originalText;
          btn.classList.remove('copied');
        }, 2000);
      }
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  }

  _retryMessage() {
    // Dispatch event for parent to handle
    this.dispatchEvent(new CustomEvent('retry-message', {
      bubbles: true,
      detail: { messageId: this._messageId, content: this._content }
    }));
  }

  _sendFeedback(type) {
    // Dispatch event for parent to handle
    this.dispatchEvent(new CustomEvent('message-feedback', {
      bubbles: true,
      detail: { messageId: this._messageId, feedback: type }
    }));
  }

  _escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  _toggleReasoning() {
    this._reasoningExpanded = !this._reasoningExpanded;
    const content = this.querySelector('.reasoning-content');
    const toggle = this.querySelector('.reasoning-toggle');
    if (content) {
      content.style.display = this._reasoningExpanded ? 'block' : 'none';
    }
    if (toggle) {
      toggle.textContent = this._reasoningExpanded ? '−' : '+';
    }
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
    this._applySyntaxHighlighting();
    this._setupEventListeners();
  }

  getReasoning() {
    return this._reasoning;
  }

  appendContent(chunk) {
    this._content += chunk;
    const contentDiv = this.querySelector('.message-content');
    if (contentDiv && this._role !== 'assistant') {
      // For user messages, append plain text
      contentDiv.textContent += chunk;
    } else if (contentDiv && this._role === 'assistant') {
      // For assistant messages, re-render full markdown (context-sensitive)
      contentDiv.innerHTML = this._renderMarkdown(this._content);
      // Re-apply syntax highlighting to new code blocks
      this._applySyntaxHighlighting();
    } else {
      this._render();
      this._applySyntaxHighlighting();
      this._setupEventListeners();
    }
  }

  appendReasoning(chunk) {
    this._reasoning += chunk;
    const reasoningContent = this.querySelector('.reasoning-content');
    if (reasoningContent) {
      reasoningContent.textContent += chunk;
    } else {
      this._render();
      this._applySyntaxHighlighting();
      this._setupEventListeners();
      this._reasoningExpanded = true;
      const content = this.querySelector('.reasoning-content');
      const toggle = this.querySelector('.reasoning-toggle');
      if (content) content.style.display = 'block';
      if (toggle) toggle.textContent = '−';
    }
  }
}

// Register the custom element
customElements.define('chat-message', ChatMessage);
