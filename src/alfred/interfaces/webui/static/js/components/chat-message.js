/**
 * Chat Message Web Component with Interleaved Content Support
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
 * 
 * Interleaved Content:
 *   This component supports interleaved content blocks (text, reasoning, tool calls)
 *   that appear in chronological order. Each block has a sequence number for ordering.
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
    this._isConnected = false;

    // Interleaved content blocks
    this._contentBlocks = []; // Array of {type, sequence, content, metadata, element}
    this._sequenceCounter = 0;
    this._textAccumulator = ''; // Accumulates text content
    this._reasoningAccumulator = ''; // Accumulates reasoning content
  }

  static get observedAttributes() {
    return ['role', 'content', 'timestamp', 'message-id', 'editable', 'data-message-state'];
  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (oldValue === newValue) return;

    switch (name) {
      case 'role':
        this._role = newValue || 'user';
        if (this._isConnected) this._render();
        break;
      case 'content':
        this._content = newValue || '';
        this._textAccumulator = this._content;
        if (this._isConnected) {
          this._updateTextBlock(this._content);
        }
        break;
      case 'timestamp':
        this._timestamp = newValue;
        if (this._isConnected) this._renderHeader();
        break;
      case 'message-id':
        this._messageId = newValue;
        break;
      case 'editable':
        this._editable = newValue !== null && newValue !== 'false';
        if (this._isConnected) this._renderActions();
        break;
      case 'data-message-state':
        this._messageState = newValue || 'idle';
        this._syncStateClasses();
        break;
    }
  }

  /**
   * Update just the text content block without full re-render
   */
  _updateTextBlock(content) {
    const lastBlock = this._contentBlocks[this._contentBlocks.length - 1];

    if (!lastBlock || lastBlock.type !== 'text') {
      // Create new text block
      this._contentBlocks.push({
        type: 'text',
        sequence: this._nextSequence(),
        content: content,
        metadata: { isStreaming: false }
      });
      this._renderContentBlocks();
    } else {
      // Update existing text block
      lastBlock.content = content;
      // Find and update the DOM element directly for performance
      const container = this._getContentBlocksContainer();
      if (container) {
        const textElement = container.querySelector('.text-block[data-sequence="' + lastBlock.sequence + '"]');
        if (textElement) {
          if (this._role === 'assistant') {
            textElement.innerHTML = this._renderMarkdown(content);
            this._applySyntaxHighlighting();
          } else {
            textElement.textContent = content;
          }
        } else {
          // Element not found, re-render all blocks
          this._renderContentBlocks();
        }
      }
    }
  }

  /**
   * Render just the header section
   */
  _renderHeader() {
    const header = this.querySelector('.message-header');
    if (header) {
      const avatar = this._getAvatar();
      const displayName = this._getDisplayName();
      const timeDisplay = this._formatTime();
      header.innerHTML = `
        <span class="message-avatar" aria-hidden="true">${avatar}</span>
        <span class="message-role">${displayName}</span>
        ${timeDisplay ? `<span class="message-time">${timeDisplay}</span>` : ''}
      `;
    }
  }

  /**
   * Render just the actions section
   */
  _renderActions() {
    // Actions are part of the main render, full re-render needed for now
    if (this._isConnected) this._render();
  }

  connectedCallback() {
    this._isConnected = true;
    if (!this.hasAttribute('data-message-state')) {
      this.setAttribute('data-message-state', this._messageState);
    }
    this._render();
    this._applySyntaxHighlighting();
    this._setupEventListeners();
    
    // Ensure text block is created for initial content (even if empty)
    this._updateTextBlock(this._content);
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

  _syncStateClasses() {
    this.classList.toggle('streaming', this._messageState === 'streaming');
    this.classList.toggle('editing', this._messageState === 'editing');
  }

  /**
   * Get the next sequence number for content blocks
   */
  _nextSequence() {
    return ++this._sequenceCounter;
  }

  /**
   * Find the content block container for interleaved rendering
   */
  _getContentBlocksContainer() {
    return this.querySelector('.content-blocks');
  }

  /**
   * Render the message with interleaved content blocks
   */
  _render() {
    this._syncStateClasses();
    const roleClass = this._role.toLowerCase();
    const messageStateClass = this._messageState && this._messageState !== 'idle'
      ? ` ${this._messageState}`
      : '';
    const avatar = this._getAvatar();
    const displayName = this._getDisplayName();
    const timeDisplay = this._formatTime();

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

    // Render with content blocks container for interleaved content
    this.innerHTML = `
      <div class="message ${roleClass}${messageStateClass}">
        <div class="message-header">
          <span class="message-avatar" aria-hidden="true">${avatar}</span>
          <span class="message-role">${displayName}</span>
          ${timeDisplay ? `<span class="message-time">${timeDisplay}</span>` : ''}
        </div>
        <div class="content-blocks"></div>
        ${actionButtons}
      </div>
    `;

    // Ensure we have a text block for the main content
    this._ensureTextBlock();
    
    // Re-render all content blocks in sequence order
    this._renderContentBlocks();
  }

  /**
   * Ensure a text block exists for the main content
   */
  _ensureTextBlock() {
    const lastBlock = this._contentBlocks[this._contentBlocks.length - 1];
    if (!lastBlock || lastBlock.type !== 'text') {
      this._contentBlocks.push({
        type: 'text',
        sequence: this._nextSequence(),
        content: this._content,
        metadata: { isStreaming: false }
      });
    }
  }

  /**
   * Render all content blocks in sequence order
   */
  _renderContentBlocks() {
    const container = this._getContentBlocksContainer();
    if (!container) return;

    // Sort blocks by sequence
    const sortedBlocks = [...this._contentBlocks].sort((a, b) => a.sequence - b.sequence);
    
    container.innerHTML = '';
    
    for (const block of sortedBlocks) {
      const blockElement = this._createBlockElement(block);
      if (blockElement) {
        container.appendChild(blockElement);
      }
    }
  }

  /**
   * Create a DOM element for a content block
   */
  _createBlockElement(block) {
    switch (block.type) {
      case 'text':
        return this._createTextBlockElement(block);
      case 'reasoning':
        return this._createReasoningBlockElement(block);
      case 'tool':
        return block.element; // Tool element is already created
      default:
        return null;
    }
  }

  /**
   * Create a text block element
   */
  _createTextBlockElement(block) {
    const div = document.createElement('div');
    div.className = 'content-block text-block';
    div.dataset.sequence = block.sequence;
    
    if (this._role === 'assistant') {
      div.innerHTML = this._renderMarkdown(block.content);
    } else {
      div.textContent = block.content;
    }
    
    return div;
  }

  /**
   * Create a reasoning block element
   */
  _createReasoningBlockElement(block) {
    const isExpanded = globalReasoningExpanded !== null ? globalReasoningExpanded : this._reasoningExpanded;
    
    const div = document.createElement('div');
    div.className = 'content-block reasoning-block';
    div.dataset.sequence = block.sequence;
    
    div.innerHTML = `
      <div class="reasoning-section">
        <div class="reasoning-header" onclick="this.closest('chat-message')._toggleReasoning()">
          <span class="reasoning-icon">◈</span>
          <span class="reasoning-label">Thinking</span>
          <span class="reasoning-toggle">${isExpanded ? '−' : '+'}</span>
        </div>
        <div class="reasoning-content" style="display: ${isExpanded ? 'block' : 'none'}">
          ${this._escapeHtml(block.content)}
        </div>
      </div>
    `;
    
    return div;
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

  // ============ Interleaved Content API ============

  /**
   * Append text content (interleaved)
   * Creates a new text block or updates the current one
   */
  appendContent(chunk) {
    this._textAccumulator += chunk;
    this._content = this._textAccumulator;
    
    // Get the last block
    const lastBlock = this._contentBlocks[this._contentBlocks.length - 1];
    
    if (lastBlock && lastBlock.type === 'text' && lastBlock.metadata?.isStreaming) {
      // Continue appending to existing text block
      lastBlock.content = this._textAccumulator;
    } else {
      // Create new text block
      this._contentBlocks.push({
        type: 'text',
        sequence: this._nextSequence(),
        content: chunk,
        metadata: { isStreaming: true }
      });
    }
    
    // Re-render content blocks
    this._renderContentBlocks();
    this._applySyntaxHighlighting();
  }

  /**
   * Append reasoning content (interleaved)
   * Creates a new reasoning block each time (allows multiple reasoning blocks)
   */
  appendReasoning(chunk) {
    // Get the last block
    const lastBlock = this._contentBlocks[this._contentBlocks.length - 1];
    
    if (lastBlock && lastBlock.type === 'reasoning') {
      // Continue appending to existing reasoning block
      lastBlock.content += chunk;
    } else {
      // Create new reasoning block
      this._contentBlocks.push({
        type: 'reasoning',
        sequence: this._nextSequence(),
        content: chunk,
        metadata: {}
      });
      
      // Use global state if set, otherwise default to expanded for new reasoning
      this._reasoningExpanded = globalReasoningExpanded !== null ? globalReasoningExpanded : true;
    }
    
    // Update total reasoning
    this._reasoning = (this._reasoning || '') + chunk;
    this._reasoningAccumulator = this._reasoning;
    
    // Re-render content blocks
    this._renderContentBlocks();
  }

  /**
   * Add a tool call block (interleaved)
   * Tool calls are always added as new blocks
   */
  appendToolCall(toolCallElement) {
    // Add as new block at current sequence
    const toolBlock = {
      type: 'tool',
      sequence: this._nextSequence(),
      content: '',
      metadata: { toolCallId: toolCallElement.getAttribute('tool-call-id') },
      element: toolCallElement
    };
    
    this._contentBlocks.push(toolBlock);
    
    // Re-render content blocks
    this._renderContentBlocks();
  }

  /**
   * Insert content at a specific position (for precise interleaving)
   * This allows inserting content between existing blocks
   */
  insertContentAt(type, content, position, metadata = {}) {
    const block = {
      type,
      sequence: position,
      content,
      metadata
    };
    
    this._contentBlocks.push(block);
    
    // Re-sort and render
    this._renderContentBlocks();
    
    if (type === 'text') {
      this._applySyntaxHighlighting();
    }
  }

  // ============ Legacy API (for backward compatibility) ============

  setContent(content) {
    this._content = content;
    this._textAccumulator = content;
    this.setAttribute('content', content);
    
    // Update or create main text block
    let textBlock = this._contentBlocks.find(b => b.type === 'text' && b.metadata?.isMainText);
    if (!textBlock) {
      textBlock = {
        type: 'text',
        sequence: this._nextSequence(),
        content: content,
        metadata: { isMainText: true }
      };
      this._contentBlocks.push(textBlock);
    } else {
      textBlock.content = content;
    }
    
    this._renderContentBlocks();
    this._applySyntaxHighlighting();
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
    this._reasoningAccumulator = reasoning;
    
    // Update or create reasoning block
    let reasoningBlock = this._contentBlocks.find(b => b.type === 'reasoning');
    if (!reasoningBlock) {
      reasoningBlock = {
        type: 'reasoning',
        sequence: this._nextSequence(),
        content: reasoning,
        metadata: {}
      };
      this._contentBlocks.push(reasoningBlock);
      
      if (globalReasoningExpanded !== null) {
        this._reasoningExpanded = globalReasoningExpanded;
      }
    } else {
      reasoningBlock.content = reasoning;
    }
    
    this._renderContentBlocks();
    this._applySyntaxHighlighting();
    this._setupEventListeners();
    this._updateReasoningVisibility();
  }

  getReasoning() {
    return this._reasoning;
  }

  setToolCalls(toolCalls) {
    // Clear existing tool blocks
    this._contentBlocks = this._contentBlocks.filter(b => b.type !== 'tool');
    
    // Add new tool blocks
    toolCalls.forEach((toolCallData) => {
      const toolCall = document.createElement('tool-call');
      toolCall.setAttribute('tool-call-id', toolCallData.toolCallId || toolCallData.tool_call_id || '');
      toolCall.setAttribute('tool-name', toolCallData.toolName || toolCallData.tool_name || '');
      toolCall.setAttribute('arguments', JSON.stringify(toolCallData.arguments || {}));
      toolCall.setAttribute('status', toolCallData.status || 'success');
      toolCall.setAttribute('output', toolCallData.output || '');
      toolCall.setAttribute('expanded', (toolCallData.status || '') === 'running' ? 'true' : 'false');
      
      this._contentBlocks.push({
        type: 'tool',
        sequence: this._nextSequence(),
        content: '',
        metadata: { toolCallId: toolCall.getAttribute('tool-call-id') },
        element: toolCall
      });
    });
    
    this._renderContentBlocks();
  }
}

// Register the custom element
customElements.define('chat-message', ChatMessage);
