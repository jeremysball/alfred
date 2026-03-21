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
        return '◉'; // Double circle for system
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

    // Build action buttons for all non-system messages - minimal icon-only design
    const actionButtons = this._role !== 'system'
      ? `<div class="message-actions">
          <button class="message-action icon-only" data-action="copy" title="Copy">
            ⧉
          </button>
          ${this._role === 'assistant' ? `<button class="message-action icon-only" data-action="retry" title="Regenerate">
            ↻
          </button>` : ''}
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

    // Create custom renderer to open links in new tab
    const renderer = new marked.Renderer();
    const originalLinkRenderer = renderer.link.bind(renderer);
    renderer.link = (href, title, text) => {
      const html = originalLinkRenderer(href, title, text);
      return html.replace('<a ', '<a target="_blank" rel="noopener noreferrer" ');
    };

    // Configure marked options
    marked.setOptions({
      gfm: true,              // GitHub Flavored Markdown (tables, etc.)
      breaks: true,           // Convert line breaks to <br>
      headerIds: false,       // Don't add ids to headers
      mangle: false,          // Don't mangle email addresses
      renderer: renderer,     // Use custom renderer
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
    // Use event delegation for action buttons
    this.addEventListener('click', (e) => {
      const actionBtn = e.target.closest('[data-action]');
      if (!actionBtn) return;

      const action = actionBtn.getAttribute('data-action');

      switch (action) {
        case 'copy':
          this._copyToClipboard(actionBtn);
          break;
        case 'retry':
          this._retryMessage();
          break;
      }
    });
  }

  async _copyToClipboard(btn) {
    const textToCopy = this._content;

    // Try modern clipboard API first
    if (navigator.clipboard && navigator.clipboard.writeText) {
      try {
        await navigator.clipboard.writeText(textToCopy);
        this._showCopyFeedback(btn);
        return;
      } catch (err) {
        console.log('Clipboard API failed, trying fallback');
      }
    }

    // Fallback: use execCommand
    try {
      const textarea = document.createElement('textarea');
      textarea.value = textToCopy;
      textarea.style.position = 'fixed';
      textarea.style.left = '-9999px';
      textarea.style.top = '0';
      document.body.appendChild(textarea);
      textarea.focus();
      textarea.select();

      const successful = document.execCommand('copy');
      document.body.removeChild(textarea);

      if (successful) {
        this._showCopyFeedback(btn);
      } else {
        console.error('execCommand copy failed');
      }
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  }

  _showCopyFeedback(btn) {
    if (!btn) return;
    const originalText = btn.textContent;
    btn.textContent = '✓';
    btn.classList.add('copied');
    setTimeout(() => {
      btn.textContent = originalText;
      btn.classList.remove('copied');
    }, 800);
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
