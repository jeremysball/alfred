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
 *   - editable: Boolean flag that shows the edit action for user messages
 *   - data-message-state: UI state for the message surface ('idle' | 'streaming' | 'editing')
 */
// Global reasoning expanded state - shared across all reasoning blocks
// null = no global preference set yet, true/false = expand/collapse all
let globalReasoningExpanded = null;

class ChatMessage extends HTMLElement {
  constructor() {
    super();
    this._content = '';
    this._role = 'user';
    this._timestamp = null;
    this._reasoning = '';
    this._reasoningExpanded = false;
    this._messageId = null;
    this._messageState = 'idle';
    this._editable = false;
    this._copied = false;
  }

  static get observedAttributes() {
    return ['role', 'content', 'timestamp', 'message-id', 'editable', 'data-message-state'];
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
      case 'editable':
        this._editable = newValue !== null && newValue !== 'false';
        break;
      case 'data-message-state':
        this._messageState = newValue || 'idle';
        break;
    }
    this._render();
  }

  connectedCallback() {
    if (!this.hasAttribute('data-message-state')) {
      this.setAttribute('data-message-state', this._messageState);
    }
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

  _getToolCallsContainer() {
    return this.querySelector('.tool-calls');
  }

  _syncStateClasses() {
    this.classList.toggle('streaming', this._messageState === 'streaming');
    this.classList.toggle('editing', this._messageState === 'editing');
  }

  _render() {
    this._syncStateClasses();
    const roleClass = this._role.toLowerCase();
    const messageStateClass = this._messageState && this._messageState !== 'idle'
      ? ` ${this._messageState}`
      : '';
    const avatar = this._getAvatar();
    const displayName = this._getDisplayName();
    const timeDisplay = this._formatTime();
    const existingToolCalls = Array.from(this.querySelectorAll('.tool-calls > tool-call'));

    // System messages are simpler
    if (this._role === 'system') {
      this.innerHTML = `
        <div class="message ${roleClass}${messageStateClass}">
          <div class="message-bubble">
            <span class="message-avatar-small">${avatar}</span>
            <span class="message-content">${this._escapeHtml(this._content)}</span>
          </div>
        </div>
      `;
      return;
    }

    // Use global reasoning state if set, otherwise use local state
    const isReasoningExpanded = globalReasoningExpanded !== null ? globalReasoningExpanded : this._reasoningExpanded;

    // Build reasoning section if present
    const reasoningSection = this._reasoning
      ? `<div class="reasoning-section">
          <div class="reasoning-header" onclick="this.closest('chat-message')._toggleReasoning()">
            <span class="reasoning-icon">◈</span>
            <span class="reasoning-label">Thinking</span>
            <span class="reasoning-toggle">${isReasoningExpanded ? '−' : '+'}</span>
          </div>
          <div class="reasoning-content" style="display: ${isReasoningExpanded ? 'block' : 'none'}">
            ${this._escapeHtml(this._reasoning)}
          </div>
        </div>`
      : '';

    // Build action buttons for all non-system messages - minimal icon-only design
    const actionButtons = this._role !== 'system'
      ? `<div class="message-actions">
          <button class="message-action icon-only" data-action="copy" title="Copy" aria-label="Copy message">
            ⧉
          </button>
          ${this._role === 'assistant'
            ? `<button class="message-action icon-only" data-action="retry" title="Regenerate" aria-label="Regenerate response">
            ↻
          </button>`
            : ''}
          ${this._role === 'user' && this._editable
            ? `<button class="message-action icon-only" data-action="edit" title="Edit" aria-label="Edit message">
            ✎
          </button>`
            : ''}
        </div>`
      : '';

    // Render content: markdown for assistant, plain text for user
    const renderedContent = this._role === 'assistant'
      ? this._renderMarkdown(this._content)
      : this._escapeHtml(this._content);

    this.innerHTML = `
      <div class="message ${roleClass}${messageStateClass}">
        <div class="message-header">
          <span class="message-avatar" aria-hidden="true">${avatar}</span>
          <span class="message-role">${displayName}</span>
          ${timeDisplay ? `<span class="message-time">${timeDisplay}</span>` : ''}
        </div>
        ${reasoningSection}
        <div class="tool-calls"></div>
        <div class="message-bubble">
          <div class="message-content">${renderedContent}</div>
        </div>
        ${actionButtons}
      </div>
    `;

    const toolCallsContainer = this._getToolCallsContainer();
    if (toolCallsContainer && existingToolCalls.length > 0) {
      existingToolCalls.forEach((toolCall) => {
        toolCallsContainer.appendChild(toolCall);
      });
    }
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
        case 'edit':
          this._editMessage();
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
      composed: true,
      detail: { messageId: this._messageId, content: this._content }
    }));
  }

  _editMessage() {
    // Dispatch event for parent to handle
    this.dispatchEvent(new CustomEvent('edit-message', {
      bubbles: true,
      composed: true,
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
    // Update global state so all reasoning blocks (past, present, future) follow this preference
    globalReasoningExpanded = this._reasoningExpanded;
    // Apply the change to all existing reasoning sections
    document.querySelectorAll('chat-message').forEach((msg) => {
      if (msg._reasoning && msg !== this) {
        msg._reasoningExpanded = globalReasoningExpanded;
        msg._updateReasoningVisibility();
      }
    });
    this._updateReasoningVisibility();
  }

  _updateReasoningVisibility() {
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

  setMessageState(state) {
    const nextState = state === 'streaming' || state === 'editing' ? state : 'idle';
    if (this._messageState === nextState && this.getAttribute('data-message-state') === nextState) {
      return;
    }

    this._messageState = nextState;
    this._syncStateClasses();
    this.setAttribute('data-message-state', nextState);
  }

  getMessageState() {
    return this._messageState;
  }

  setEditable(editable) {
    const nextEditable = Boolean(editable);
    if (this._editable === nextEditable) {
      return;
    }

    this._editable = nextEditable;
    if (this._editable) {
      this.setAttribute('editable', 'true');
    } else {
      this.removeAttribute('editable');
    }
  }

  getEditable() {
    return this._editable;
  }

  setReasoning(reasoning) {
    this._reasoning = reasoning;
    // Use global state if set, otherwise keep current local state
    if (globalReasoningExpanded !== null) {
      this._reasoningExpanded = globalReasoningExpanded;
    }
    this._render();
    this._applySyntaxHighlighting();
    this._setupEventListeners();
  }

  getReasoning() {
    return this._reasoning;
  }

  appendToolCall(toolCallElement) {
    const container = this._getToolCallsContainer();
    if (container) {
      container.appendChild(toolCallElement);
    } else {
      this._render();
      this._applySyntaxHighlighting();
      this._setupEventListeners();
      const toolCallsContainer = this._getToolCallsContainer();
      if (toolCallsContainer) {
        toolCallsContainer.appendChild(toolCallElement);
      }
    }
  }

  setToolCalls(toolCalls) {
    const container = this._getToolCallsContainer();
    if (!container) {
      this._render();
      this._applySyntaxHighlighting();
      this._setupEventListeners();
    }

    const toolCallsContainer = this._getToolCallsContainer();
    if (!toolCallsContainer) return;

    toolCallsContainer.innerHTML = '';
    toolCalls.forEach((toolCallData) => {
      const toolCall = document.createElement('tool-call');
      toolCall.setAttribute('tool-call-id', toolCallData.toolCallId || toolCallData.tool_call_id || '');
      toolCall.setAttribute('tool-name', toolCallData.toolName || toolCallData.tool_name || '');
      toolCall.setAttribute('arguments', JSON.stringify(toolCallData.arguments || {}));
      toolCall.setAttribute('status', toolCallData.status || 'success');
      toolCall.setAttribute('output', toolCallData.output || '');
      toolCall.setAttribute('expanded', (toolCallData.status || '') === 'running' ? 'true' : 'false');
      toolCallsContainer.appendChild(toolCall);
    });
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
      // Use global state if set, otherwise default to expanded for new reasoning
      this._reasoningExpanded = globalReasoningExpanded !== null ? globalReasoningExpanded : true;
      this._render();
      this._applySyntaxHighlighting();
      this._setupEventListeners();
      this._updateReasoningVisibility();
    }
  }
}

// Register the custom element
customElements.define('chat-message', ChatMessage);
