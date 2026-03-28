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
    this._content = "";
    this._role = "user";
    this._timestamp = null;
    this._reasoning = "";
    this._reasoningExpanded = false;
    this._messageId = null;
    this._messageState = "idle";
    this._editable = false;
    this._copied = false;
    this._isConnected = false;
    this._isEditingInline = false;

    // Interleaved content blocks
    this._contentBlocks = []; // Array of {type, sequence, content, metadata, element}
    this._sequenceCounter = 0;
    this._textAccumulator = ""; // Accumulates text content
    this._currentTextBlock = null;
    this._reasoningAccumulator = ""; // Accumulates reasoning content

    // Performance timing instrumentation
    this._perfStats = {
      appendContentCalls: 0,
      totalAppendTime: 0,
      markdownParseTime: 0,
      highlightTime: 0,
      domRebuildTime: 0,
      lastChunkSize: 0,
      totalContentLength: 0,
    };
  }

  static get observedAttributes() {
    return ["role", "content", "timestamp", "message-id", "editable", "data-message-state"];
  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (oldValue === newValue) return;

    switch (name) {
      case "role":
        this._role = newValue || "user";
        if (this._isConnected) this._render();
        break;
      case "content":
        this._content = newValue || "";
        this._textAccumulator = this._content;
        if (this._isConnected) {
          this._updateTextBlock(this._content);
        }
        break;
      case "timestamp":
        this._timestamp = newValue;
        if (this._isConnected) this._renderHeader();
        break;
      case "message-id":
        this._messageId = newValue;
        break;
      case "editable":
        this._editable = newValue !== null && newValue !== "false";
        if (this._isConnected) this._renderActions();
        break;
      case "data-message-state":
        this._messageState = newValue || "idle";
        this._syncStateClasses();
        break;
    }
  }

  /**
   * Update just the text content block without full re-render
   */
  _updateTextBlock(content) {
    // Find the most recent text block (not just the last block)
    // This ensures we update the main text even if tools were added
    const textBlocks = this._contentBlocks.filter((block) => block.type === "text");
    const lastTextBlock = textBlocks[textBlocks.length - 1];

    if (!lastTextBlock) {
      // Create new text block
      this._contentBlocks.push({
        type: "text",
        sequence: this._nextSequence(),
        content: content,
        metadata: { isStreaming: false },
      });
      this._renderContentBlocks();
    } else {
      // Update existing text block
      lastTextBlock.content = content;
      // Find and update the DOM element directly for performance
      const container = this._getContentBlocksContainer();
      if (container) {
        const textElement = container.querySelector(
          `.text-block[data-sequence="${lastTextBlock.sequence}"]`,
        );
        if (textElement) {
          if (this._role === "assistant") {
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
   * Set reasoning scroll position without smooth-scroll animation fighting streaming updates.
   */
  _setReasoningScrollTop(contentElement, scrollTop) {
    const previousBehavior = contentElement.style.scrollBehavior;
    contentElement.style.scrollBehavior = "auto";
    contentElement.scrollTop = scrollTop;
    contentElement.style.scrollBehavior = previousBehavior;
  }

  /**
   * Update just the reasoning content block without full re-render
   * Preserves scroll position unless user was already at bottom (auto-stick)
   */
  _updateReasoningBlock(content) {
    // Find the most recent reasoning block
    const reasoningBlocks = this._contentBlocks.filter((block) => block.type === "reasoning");
    const lastReasoningBlock = reasoningBlocks[reasoningBlocks.length - 1];

    if (!lastReasoningBlock) {
      // Create new reasoning block
      this._contentBlocks.push({
        type: "reasoning",
        sequence: this._nextSequence(),
        content: content,
        metadata: {},
      });
      this._reasoningExpanded = globalReasoningExpanded !== null ? globalReasoningExpanded : true;
      this._renderContentBlocks();
      return;
    }

    // Update existing reasoning block
    lastReasoningBlock.content = content;

    // Find and update the DOM element directly for performance
    const container = this._getContentBlocksContainer();
    if (container) {
      const reasoningElement = container.querySelector(
        `.reasoning-block[data-sequence="${lastReasoningBlock.sequence}"]`,
      );
      if (reasoningElement) {
        const contentElement = reasoningElement.querySelector(".reasoning-content");
        if (contentElement) {
          // Capture scroll state before update
          const scrollTopBefore = contentElement.scrollTop;
          const scrollHeightBefore = contentElement.scrollHeight;
          const clientHeight = contentElement.clientHeight;
          const atBottom = scrollTopBefore + clientHeight >= scrollHeightBefore - 8;

          // Update content
          contentElement.innerHTML = this._renderMarkdown(content);
          this._applySyntaxHighlighting();

          // Restore scroll position immediately so rapid streaming chunks do not
          // see a stale pre-scroll state and "fight" the bottom pinning logic.
          if (atBottom) {
            this._setReasoningScrollTop(contentElement, contentElement.scrollHeight);
            // Re-apply after layout settles in case markdown rendering changes height.
            requestAnimationFrame(() => {
              this._setReasoningScrollTop(contentElement, contentElement.scrollHeight);
            });
          } else {
            this._setReasoningScrollTop(
              contentElement,
              Math.min(scrollTopBefore, contentElement.scrollHeight),
            );
          }
        } else {
          // Content element not found, re-render all blocks
          this._renderContentBlocks();
        }
      } else {
        // Element not found, re-render all blocks
        this._renderContentBlocks();
      }
    }
  }

  /**
   * Render just the header section
   */
  _renderHeader() {
    const header = this.querySelector(".message-header");
    if (header) {
      const avatar = this._getAvatar();
      const displayName = this._getDisplayName();
      const timeDisplay = this._formatTime();
      header.innerHTML = `
        <span class="message-avatar" aria-hidden="true">${avatar}</span>
        <span class="message-role">${displayName}</span>
        ${timeDisplay ? `<span class="message-time">${timeDisplay}</span>` : ""}
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
    if (!this.hasAttribute("data-message-state")) {
      this.setAttribute("data-message-state", this._messageState);
    }
    this._render();
    this._applySyntaxHighlighting();
    this._setupEventListeners();

    // Ensure text block is created for initial content (even if empty)
    this._updateTextBlock(this._content);
  }

  _getAvatar() {
    switch (this._role) {
      case "user":
        // User: person icon
        return '<svg class="message-avatar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>';
      case "assistant":
        // Alfred: bot/robot head icon
        return '<svg class="message-avatar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/><path d="M12 7v4"/><line x1="8" y1="16" x2="8" y2="16"/><line x1="16" y1="16" x2="16" y2="16"/></svg>';
      case "system":
        // System: gear icon
        return '<svg class="message-avatar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>';
      default:
        // Default: empty circle
        return '<svg class="message-avatar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/></svg>';
    }
  }

  _getDisplayName() {
    switch (this._role) {
      case "assistant":
        return "Alfred";
      case "user":
        return "You";
      case "system":
        return "System";
      default:
        return this._role;
    }
  }

  _formatTime() {
    if (!this._timestamp) return "";
    const date = new Date(this._timestamp);
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  _syncStateClasses() {
    const isStreaming = this._messageState === "streaming";
    this.classList.toggle("streaming", isStreaming);
    this.classList.toggle("editing", this._messageState === "editing");

    // Update existing reasoning blocks' streaming state
    const reasoningBlocks = this.querySelectorAll(".reasoning-block");
    reasoningBlocks.forEach((block) => {
      block.classList.toggle("streaming", isStreaming);
    });
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
    return this.querySelector(".content-blocks");
  }

  /**
   * Render the message with interleaved content blocks
   */
  _render() {
    this._syncStateClasses();
    const roleClass = this._role.toLowerCase();
    const messageStateClass =
      this._messageState && this._messageState !== "idle" ? ` ${this._messageState}` : "";
    const avatar = this._getAvatar();
    const displayName = this._getDisplayName();
    const timeDisplay = this._formatTime();

    // System messages are simpler
    if (this._role === "system") {
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
    const actionButtons =
      this._role !== "system"
        ? `<div class="message-actions">
          <button class="message-action icon-only" data-action="copy" title="Copy" aria-label="Copy message">
            <svg class="message-action-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
          </button>
          ${
            this._role === "assistant"
              ? `<button class="message-action icon-only" data-action="retry" title="Regenerate" aria-label="Regenerate response">
            <svg class="message-action-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"></polyline><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path></svg>
          </button>`
              : ""
          }
          ${
            // _role === 'user' && this._editable
            this._role === "user" && this._editable
              ? `<button class="message-action icon-only" data-action="edit" title="Edit" aria-label="Edit message">
            <svg class="message-action-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"></path></svg>
          </button>`
              : ""
          }
        </div>`
        : "";

    // Render with content blocks container for interleaved content
    this.innerHTML = `
      <div class="message ${roleClass}${messageStateClass}">
        <div class="message-header">
          <span class="message-avatar" aria-hidden="true">${avatar}</span>
          <span class="message-role">${displayName}</span>
          ${timeDisplay ? `<span class="message-time">${timeDisplay}</span>` : ""}
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
    // Check if ANY text block exists (not just the last one)
    const hasTextBlock = this._contentBlocks.some((block) => block.type === "text");
    if (!hasTextBlock) {
      this._contentBlocks.push({
        type: "text",
        sequence: this._nextSequence(),
        content: this._content,
        metadata: { isStreaming: false },
      });
    }
  }

  /**
   * Refresh the active text block reference based on current block ordering.
   * Returns the last text block when the message currently ends with text,
   * otherwise clears the active reference so the next text chunk starts fresh.
   */
  _refreshCurrentTextBlockReference() {
    const sortedBlocks = [...this._contentBlocks].sort((a, b) => a.sequence - b.sequence);
    const lastBlock = sortedBlocks[sortedBlocks.length - 1];
    if (lastBlock && lastBlock.type === "text") {
      this._currentTextBlock = lastBlock;
      return lastBlock;
    }

    this._currentTextBlock = null;
    return null;
  }

  /**
   * Render all content blocks in sequence order
   */
  _renderContentBlocks() {
    const startTime = performance.now();
    const container = this._getContentBlocksContainer();
    if (!container) return;

    // Save scroll positions of existing reasoning blocks before clearing
    const scrollPositions = this._saveReasoningScrollPositions();

    // Sort blocks by sequence
    const sortedBlocks = [...this._contentBlocks].sort((a, b) => a.sequence - b.sequence);

    container.innerHTML = "";

    for (const block of sortedBlocks) {
      const blockElement = this._createBlockElement(block);
      if (blockElement) {
        container.appendChild(blockElement);
      }
    }

    // Restore scroll positions and auto-scroll only the last (active) reasoning block
    this._restoreReasoningScrollPositions(scrollPositions);

    const elapsed = performance.now() - startTime;
    this._perfStats.domRebuildTime += elapsed;
  }

  /**
   * Save scroll positions of all reasoning content blocks
   * Returns a Map of sequence number to scrollTop value
   */
  _saveReasoningScrollPositions() {
    const scrollPositions = new Map();
    const reasoningBlocks = this.querySelectorAll(".reasoning-block");
    reasoningBlocks.forEach((block) => {
      const content = block.querySelector(".reasoning-content");
      const sequence = block.dataset.sequence;
      if (content && sequence) {
        scrollPositions.set(sequence, content.scrollTop);
      }
    });
    return scrollPositions;
  }

  /**
   * Restore scroll positions to reasoning blocks and auto-scroll only the last one
   * @param {Map} scrollPositions - Map of sequence to scrollTop values
   */
  _restoreReasoningScrollPositions(scrollPositions) {
    const reasoningBlocks = this.querySelectorAll(".reasoning-block");
    const lastBlockIndex = reasoningBlocks.length - 1;
    let lastBlockContent = null;

    reasoningBlocks.forEach((block, index) => {
      const content = block.querySelector(".reasoning-content");
      const sequence = block.dataset.sequence;
      if (!content || !sequence) return;

      // Don't scroll collapsed blocks
      if (content.style.display === "none") return;

      if (index === lastBlockIndex) {
        // Save reference to last block for deferred scroll
        lastBlockContent = content;
      } else if (scrollPositions.has(sequence)) {
        // Restore previous scroll position for older blocks
        this._setReasoningScrollTop(content, scrollPositions.get(sequence));
      }
    });

    // Auto-scroll the last (active) reasoning block after the browser renders
    // This prevents flickering by ensuring scroll happens after content is laid out
    if (lastBlockContent) {
      requestAnimationFrame(() => {
        this._setReasoningScrollTop(lastBlockContent, lastBlockContent.scrollHeight);
      });
    }
  }

  /**
   * Create a DOM element for a content block
   */
  _createBlockElement(block) {
    switch (block.type) {
      case "text":
        return this._createTextBlockElement(block);
      case "reasoning":
        return this._createReasoningBlockElement(block);
      case "tool":
        return block.element; // Tool element is already created
      default:
        return null;
    }
  }

  /**
   * Create a text block element
   */
  _createTextBlockElement(block) {
    const div = document.createElement("div");
    div.className = "content-block text-block";
    div.dataset.sequence = block.sequence;

    if (this._role === "assistant") {
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
    const isExpanded =
      globalReasoningExpanded !== null ? globalReasoningExpanded : this._reasoningExpanded;
    const isStreaming = this._messageState === "streaming";

    const div = document.createElement("div");
    div.className = `content-block reasoning-block${isStreaming ? " streaming" : ""}`;
    div.dataset.sequence = block.sequence;

    const section = document.createElement("div");
    section.className = "reasoning-section";

    const header = document.createElement("div");
    header.className = "reasoning-header";
    header.innerHTML = `
      <span class="reasoning-icon">◈</span>
      <span class="reasoning-label">Thinking</span>
      <span class="reasoning-toggle">${isExpanded ? "−" : "+"}</span>
    `;
    // Click anywhere on header to toggle (but not content)
    header.addEventListener("click", (e) => {
      e.stopPropagation();
      this._toggleReasoning();
    });

    const content = document.createElement("div");
    content.className = "reasoning-content";
    content.style.display = isExpanded ? "block" : "none";
    // Render reasoning content with markdown
    content.innerHTML = this._renderMarkdown(block.content);

    section.appendChild(header);
    section.appendChild(content);
    div.appendChild(section);

    return div;
  }

  _renderMarkdown(content) {
    const startTime = performance.now();

    // Check if marked is available
    if (typeof marked === "undefined") {
      console.warn("marked.js not loaded, falling back to plain text");
      return this._escapeHtml(content);
    }

    // Create custom renderer to open links in new tab
    const renderer = new marked.Renderer();
    const originalLinkRenderer = renderer.link.bind(renderer);
    renderer.link = (href, title, text) => {
      const html = originalLinkRenderer(href, title, text);
      return html.replace("<a ", '<a target="_blank" rel="noopener noreferrer" ');
    };

    // Configure marked options
    marked.setOptions({
      gfm: true, // GitHub Flavored Markdown (tables, etc.)
      breaks: true, // Convert line breaks to <br>
      headerIds: false, // Don't add ids to headers
      mangle: false, // Don't mangle email addresses
      renderer: renderer, // Use custom renderer
    });

    // Parse markdown
    const html = marked.parse(content);

    const elapsed = performance.now() - startTime;
    this._perfStats.markdownParseTime += elapsed;

    return html;
  }

  _applySyntaxHighlighting() {
    const startTime = performance.now();

    // Check if highlight.js is available
    if (typeof hljs === "undefined") {
      console.warn("highlight.js not loaded, skipping syntax highlighting");
      return;
    }

    // Find all code blocks and apply highlighting
    const codeBlocks = this.querySelectorAll("pre code");
    codeBlocks.forEach((block) => {
      hljs.highlightElement(block);
    });

    const elapsed = performance.now() - startTime;
    this._perfStats.highlightTime += elapsed;
  }

  _setupEventListeners() {
    // Toggle active state on message tap (for mobile)
    this.addEventListener("click", (e) => {
      // Don't toggle if clicking on buttons, links, or interactive elements
      if (
        e.target.closest("[data-action]") ||
        e.target.closest("a") ||
        e.target.closest("button") ||
        e.target.closest(".reasoning-header")
      ) {
        return;
      }

      // Toggle active class for showing/hiding action buttons on mobile
      this.classList.toggle("active");

      // Remove active class from other messages (only one active at a time)
      const allMessages = this.parentElement?.querySelectorAll("chat-message");
      allMessages?.forEach((msg) => {
        if (msg !== this) {
          msg.classList.remove("active");
        }
      });
    });

    // Use event delegation for action buttons
    this.addEventListener("click", (e) => {
      const actionBtn = e.target.closest("[data-action]");
      if (!actionBtn) return;

      const action = actionBtn.getAttribute("data-action");

      switch (action) {
        case "copy":
          this._copyToClipboard(actionBtn);
          break;
        case "retry":
          this._retryMessage();
          break;
        case "edit":
          this._editMessage();
          break;
      }
    });
  }

  async _copyToClipboard(btn) {
    const textToCopy = this._content;

    // Try modern clipboard API first
    if (navigator.clipboard?.writeText) {
      try {
        await navigator.clipboard.writeText(textToCopy);
        this._showCopyFeedback(btn);
        return;
      } catch (_err) {
        console.log("Clipboard API failed, trying fallback");
      }
    }

    // Fallback: use execCommand
    try {
      const textarea = document.createElement("textarea");
      textarea.value = textToCopy;
      textarea.style.position = "fixed";
      textarea.style.left = "-9999px";
      textarea.style.top = "0";
      document.body.appendChild(textarea);
      textarea.focus();
      textarea.select();

      const successful = document.execCommand("copy");
      document.body.removeChild(textarea);

      if (successful) {
        this._showCopyFeedback(btn);
      } else {
        console.error("execCommand copy failed");
      }
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  }

  _showCopyFeedback(btn) {
    if (!btn) return;
    const originalHTML = btn.innerHTML;
    btn.innerHTML =
      '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>';
    btn.classList.add("copied");
    setTimeout(() => {
      btn.innerHTML = originalHTML;
      btn.classList.remove("copied");
    }, 800);
  }

  _retryMessage() {
    // Dispatch event for parent to handle
    this.dispatchEvent(
      new CustomEvent("retry-message", {
        bubbles: true,
        composed: true,
        detail: { messageId: this._messageId, content: this._content },
      }),
    );
  }

  _editMessage() {
    // Start inline editing instead of dispatching to composer
    this._startInlineEdit();
  }

  _startInlineEdit() {
    if (this._isEditingInline) return;

    this._isEditingInline = true;
    this._renderInlineEdit();
  }

  _cancelInlineEdit() {
    if (!this._isEditingInline) return;

    this._isEditingInline = false;
    this._render();
  }

  _saveInlineEdit() {
    if (!this._isEditingInline) return;

    const textarea = this.querySelector(".inline-edit-textarea");
    if (!textarea) return;

    const newContent = textarea.value.trim();
    if (!newContent) return; // Don't save empty content

    // Exit editing mode first
    this._isEditingInline = false;

    // Dispatch event for parent to handle the actual save
    this.dispatchEvent(
      new CustomEvent("message-edited", {
        bubbles: true,
        composed: true,
        detail: {
          messageId: this._messageId,
          oldContent: this._content,
          newContent: newContent,
        },
      }),
    );
  }

  _renderInlineEdit() {
    const roleClass = this._role.toLowerCase();
    const avatar = this._getAvatar();
    const displayName = this._getDisplayName();
    const timeDisplay = this._formatTime();

    this.innerHTML = `
      <div class="message ${roleClass} editing-inline">
        <div class="message-header">
          <span class="message-avatar" aria-hidden="true">${avatar}</span>
          <span class="message-role">${displayName}</span>
          ${timeDisplay ? `<span class="message-time">${timeDisplay}</span>` : ""}
        </div>
        <div class="inline-edit-container">
          <textarea class="inline-edit-textarea" rows="3">${this._escapeHtml(this._content)}</textarea>
          <div class="inline-edit-actions">
            <button class="inline-edit-btn cancel" data-action="cancel-edit">Cancel</button>
            <button class="inline-edit-btn save" data-action="save-edit">Save</button>
          </div>
        </div>
      </div>
    `;

    // Focus the textarea and set cursor at end
    const textarea = this.querySelector(".inline-edit-textarea");
    if (textarea) {
      textarea.focus();
      textarea.setSelectionRange(textarea.value.length, textarea.value.length);

      // Auto-resize textarea
      const resizeTextarea = () => {
        textarea.style.height = "auto";
        textarea.style.height = `${Math.min(textarea.scrollHeight, 400)}px`;
      };
      textarea.addEventListener("input", resizeTextarea);
      resizeTextarea();

      // Handle keyboard shortcuts
      textarea.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
          e.preventDefault();
          this._saveInlineEdit();
          // e.key === 'Escape'
        } else if (e.key === "Escape") {
          e.preventDefault();
          this._cancelInlineEdit();
        }
      });
    }

    // Setup button handlers
    this.querySelector('[data-action="cancel-edit"]')?.addEventListener("click", () => {
      this._cancelInlineEdit();
    });
    this.querySelector('[data-action="save-edit"]')?.addEventListener("click", () => {
      this._saveInlineEdit();
    });
  }

  _sendFeedback(type) {
    // Dispatch event for parent to handle
    this.dispatchEvent(
      new CustomEvent("message-feedback", {
        bubbles: true,
        detail: { messageId: this._messageId, feedback: type },
      }),
    );
  }

  _escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  _toggleReasoning() {
    this._reasoningExpanded = !this._reasoningExpanded;
    // Update global state so all reasoning blocks (past, present, future) follow this preference
    globalReasoningExpanded = this._reasoningExpanded;
    // Apply the change to all existing reasoning sections
    document.querySelectorAll("chat-message").forEach((msg) => {
      if (msg._reasoning && msg !== this) {
        msg._reasoningExpanded = globalReasoningExpanded;
        msg._updateReasoningVisibility();
      }
    });
    this._updateReasoningVisibility();
  }

  _updateReasoningVisibility() {
    const contents = this.querySelectorAll(".reasoning-content");
    const toggles = this.querySelectorAll(".reasoning-toggle");
    contents.forEach((content) => {
      content.style.display = this._reasoningExpanded ? "block" : "none";
    });
    toggles.forEach((toggle) => {
      toggle.textContent = this._reasoningExpanded ? "−" : "+";
    });
  }

  // ============ Interleaved Content API ============

  /**
   * Append text content (interleaved)
   * Creates a new text block or updates the current one
   */
  appendContent(chunk) {
    const startTime = performance.now();
    this._perfStats.appendContentCalls++;
    this._perfStats.lastChunkSize = chunk.length;

    this._textAccumulator += chunk;
    this._content = this._textAccumulator;
    this._perfStats.totalContentLength = this._textAccumulator.length;

    let textBlock = this._refreshCurrentTextBlockReference();

    if (textBlock) {
      // Continue appending to the current text segment.
      textBlock.content += chunk;
      textBlock.metadata = { ...(textBlock.metadata || {}), isStreaming: true };
      this._currentTextBlock = textBlock;
    } else {
      // Create a fresh text block after a tool or reasoning boundary.
      textBlock = {
        type: "text",
        sequence: this._nextSequence(),
        content: chunk,
        metadata: { isStreaming: true },
      };
      this._contentBlocks.push(textBlock);
      this._currentTextBlock = textBlock;
    }

    // Re-render content blocks
    this._renderContentBlocks();
    this._applySyntaxHighlighting();

    const elapsed = performance.now() - startTime;
    this._perfStats.totalAppendTime += elapsed;

    // Log performance warning if render takes too long
    if (elapsed > 16) {
      // 16ms = 60fps threshold
      console.warn(
        `[ChatMessage Perf] appendContent took ${elapsed.toFixed(2)}ms ` +
          `(chunk: ${chunk.length} chars, total: ${this._textAccumulator.length} chars, ` +
          `call #${this._perfStats.appendContentCalls})`,
      );
    }
  }

  /**
   * Start a new reasoning block (for when backend signals new reasoning segment)
   * Only creates a new block if the last reasoning block already has content.
   */
  startNewReasoningBlock() {
    // Don't add reasoning to user messages
    if (this._role === "user") {
      return;
    }

    // Check if the last reasoning block is empty - if so, don't create another
    const reasoningBlocks = this._contentBlocks.filter((block) => block.type === "reasoning");
    const lastReasoningBlock = reasoningBlocks[reasoningBlocks.length - 1];

    if (lastReasoningBlock && !lastReasoningBlock.content) {
      // Last block is empty and hasn't received content yet, reuse it
      return;
    }

    // Create a new empty reasoning block that subsequent chunks will append to
    this._contentBlocks.push({
      type: "reasoning",
      sequence: this._nextSequence(),
      content: "",
      metadata: {},
    });

    // New reasoning means the next visible text chunk starts a fresh block.
    this._currentTextBlock = null;

    // Use global state if set, otherwise default to expanded for new reasoning
    this._reasoningExpanded = globalReasoningExpanded !== null ? globalReasoningExpanded : true;
  }

  /**
   * Append reasoning content (interleaved)
   * Appends to the most recent reasoning block, or creates one if none exists
   */
  appendReasoning(chunk) {
    // Don't add reasoning to user messages
    if (this._role === "user") {
      return;
    }
    // Find the most recent reasoning block (not just the last block)
    // This ensures we continue updating reasoning even if tools were added after
    const reasoningBlocks = this._contentBlocks.filter((block) => block.type === "reasoning");
    const lastReasoningBlock = reasoningBlocks[reasoningBlocks.length - 1];

    // Update total reasoning
    this._reasoning = (this._reasoning || "") + chunk;
    this._reasoningAccumulator = this._reasoning;

    if (lastReasoningBlock) {
      // Continue appending to existing reasoning block using in-place update
      // This preserves scroll position unless user was already at bottom
      this._updateReasoningBlock(lastReasoningBlock.content + chunk);
    } else {
      // Create new reasoning block - requires full render
      this._contentBlocks.push({
        type: "reasoning",
        sequence: this._nextSequence(),
        content: chunk,
        metadata: {},
      });

      // Use global state if set, otherwise default to expanded for new reasoning
      this._reasoningExpanded = globalReasoningExpanded !== null ? globalReasoningExpanded : true;

      // Re-render content blocks for new block
      this._renderContentBlocks();
    }

    // Any reasoning segment breaks the current visible text segment.
    this._currentTextBlock = null;
  }

  /**
   * Add a tool call block (interleaved)
   * Tool calls are always added as new blocks
   */
  appendToolCall(toolCallElement) {
    // Add as new block at current sequence
    const toolBlock = {
      type: "tool",
      sequence: this._nextSequence(),
      content: "",
      metadata: { toolCallId: toolCallElement.getAttribute("tool-call-id") },
      element: toolCallElement,
    };

    this._contentBlocks.push(toolBlock);

    // Tool calls break the current visible text segment.
    this._currentTextBlock = null;

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
      metadata,
    };

    this._contentBlocks.push(block);

    // Re-sort and render
    this._renderContentBlocks();

    if (type === "text") {
      this._applySyntaxHighlighting();
    }
  }

  // ============ Legacy API (for backward compatibility) ============

  setContent(content) {
    this._content = content;
    this._textAccumulator = content;
    this.setAttribute("content", content);

    // Update or create main text block
    let textBlock = this._contentBlocks.find((b) => b.type === "text" && b.metadata?.isMainText);
    if (!textBlock) {
      textBlock = {
        type: "text",
        sequence: this._nextSequence(),
        content: content,
        metadata: { isMainText: true },
      };
      this._contentBlocks.push(textBlock);
    } else {
      textBlock.content = content;
    }

    this._renderContentBlocks();
    this._applySyntaxHighlighting();
    this._refreshCurrentTextBlockReference();
  }

  /**
   * Replace all visible text blocks in one shot (used for session restore).
   * Text blocks are restored in sequence order so they can interleave with
   * reasoning and tool call blocks without flattening everything into one block.
   */
  setTextBlocks(textBlocks) {
    if (this._role === "user") {
      return;
    }

    // Remove existing text blocks, keep reasoning/tool blocks intact.
    this._contentBlocks = this._contentBlocks.filter((b) => b.type !== "text");
    this._currentTextBlock = null;

    const sortedTextBlocks = Array.isArray(textBlocks)
      ? [...textBlocks].sort((a, b) => {
          const seqA = a.sequence !== undefined ? a.sequence : 0;
          const seqB = b.sequence !== undefined ? b.sequence : 0;
          return seqA - seqB;
        })
      : [];

    let fullText = "";
    sortedTextBlocks.forEach((blockData) => {
      const content = blockData.content || "";
      const sequence = blockData.sequence !== undefined ? blockData.sequence : this._nextSequence();

      this._sequenceCounter = Math.max(this._sequenceCounter, sequence);
      this._contentBlocks.push({
        type: "text",
        sequence: sequence,
        content: content,
        metadata: { isStreaming: false },
      });

      fullText += content;
    });

    this._content = fullText;
    this._textAccumulator = fullText;

    this._renderContentBlocks();
    this._applySyntaxHighlighting();
    this._refreshCurrentTextBlockReference();
  }

  getContent() {
    return this._content;
  }

  setRole(role) {
    this._role = role;
    this.setAttribute("role", role);
  }

  getRole() {
    return this._role;
  }

  setMessageState(state) {
    const nextState = state === "streaming" || state === "editing" ? state : "idle";
    if (this._messageState === nextState && this.getAttribute("data-message-state") === nextState) {
      return;
    }

    this._messageState = nextState;
    this._syncStateClasses();
    this.setAttribute("data-message-state", nextState);
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
      this.setAttribute("editable", "true");
    } else {
      this.removeAttribute("editable");
    }
  }

  getEditable() {
    return this._editable;
  }

  setReasoning(reasoning, sequence = null) {
    // Don't add reasoning to user messages
    if (this._role === "user") {
      return;
    }

    if (!reasoning) {
      this._reasoning = "";
      this._reasoningAccumulator = "";
      this._contentBlocks = this._contentBlocks.filter((b) => b.type !== "reasoning");
      this._renderContentBlocks();
      this._applySyntaxHighlighting();
      this._setupEventListeners();
      this._updateReasoningVisibility();
      this._refreshCurrentTextBlockReference();
      return;
    }

    this._reasoning = reasoning;
    this._reasoningAccumulator = reasoning;

    // Update or create reasoning block
    let reasoningBlock = this._contentBlocks.find((b) => b.type === "reasoning");
    if (!reasoningBlock) {
      // Use provided sequence (for session restore) or generate new one
      // Default to 0 for session restore so reasoning appears before content
      const blockSequence = sequence !== null ? sequence : this._nextSequence();
      if (sequence !== null) {
        this._sequenceCounter = Math.max(this._sequenceCounter, sequence);
      }

      reasoningBlock = {
        type: "reasoning",
        sequence: blockSequence,
        content: reasoning,
        metadata: {},
      };
      this._contentBlocks.push(reasoningBlock);

      if (globalReasoningExpanded !== null) {
        this._reasoningExpanded = globalReasoningExpanded;
      }
    } else {
      reasoningBlock.content = reasoning;
      // Update sequence if provided (for session restore)
      if (sequence !== null) {
        reasoningBlock.sequence = sequence;
        this._sequenceCounter = Math.max(this._sequenceCounter, sequence);
      }
    }

    this._renderContentBlocks();
    this._applySyntaxHighlighting();
    this._setupEventListeners();
    this._updateReasoningVisibility();
    this._refreshCurrentTextBlockReference();
  }

  getReasoning() {
    return this._reasoning;
  }

  /**
   * Set multiple reasoning blocks with sequences (for session restore)
   * This allows reasoning to be interleaved with tool calls
   */
  setReasoningBlocks(reasoningBlocks) {
    // Don't add reasoning to user messages
    if (this._role === "user") {
      return;
    }

    // Clear existing reasoning blocks
    this._contentBlocks = this._contentBlocks.filter((b) => b.type !== "reasoning");

    // Add new reasoning blocks with their sequences
    let totalReasoning = "";
    reasoningBlocks.forEach((blockData) => {
      const content = blockData.content || "";
      const sequence = blockData.sequence !== undefined ? blockData.sequence : this._nextSequence();

      // Update sequence counter to ensure future blocks are after this
      this._sequenceCounter = Math.max(this._sequenceCounter, sequence);

      this._contentBlocks.push({
        type: "reasoning",
        sequence: sequence,
        content: content,
        metadata: {},
      });

      totalReasoning += content;
    });

    // Update total reasoning
    this._reasoning = totalReasoning;
    this._reasoningAccumulator = totalReasoning;

    // Use global state if set, otherwise default to expanded
    if (globalReasoningExpanded !== null) {
      this._reasoningExpanded = globalReasoningExpanded;
    }

    this._renderContentBlocks();
    this._applySyntaxHighlighting();
    this._setupEventListeners();
    this._updateReasoningVisibility();
    this._refreshCurrentTextBlockReference();
  }

  setToolCalls(toolCalls) {
    // Clear existing tool blocks
    this._contentBlocks = this._contentBlocks.filter((b) => b.type !== "tool");

    // Add new tool blocks, preserving sequence from backend if available
    toolCalls.forEach((toolCallData) => {
      const toolCall = document.createElement("tool-call");
      toolCall.setAttribute(
        "tool-call-id",
        toolCallData.toolCallId || toolCallData.tool_call_id || "",
      );
      toolCall.setAttribute("tool-name", toolCallData.toolName || toolCallData.tool_name || "");
      toolCall.setAttribute("arguments", JSON.stringify(toolCallData.arguments || {}));
      toolCall.setAttribute("status", toolCallData.status || "success");
      toolCall.setAttribute("output", toolCallData.output || "");
      toolCall.setAttribute(
        "expanded",
        (toolCallData.status || "") === "running" ? "true" : "false",
      );

      // Use backend sequence if available, otherwise generate new one
      const sequence =
        toolCallData.sequence !== undefined ? toolCallData.sequence : this._nextSequence();
      // Update sequence counter to ensure future blocks are after this
      this._sequenceCounter = Math.max(this._sequenceCounter, sequence);

      this._contentBlocks.push({
        type: "tool",
        sequence: sequence,
        content: "",
        metadata: { toolCallId: toolCall.getAttribute("tool-call-id") },
        element: toolCall,
      });
    });

    this._renderContentBlocks();
    this._refreshCurrentTextBlockReference();
  }

  /**
   * Print performance statistics to console
   */
  printPerfStats() {
    const stats = this._perfStats;
    const avgAppendTime =
      stats.appendContentCalls > 0
        ? (stats.totalAppendTime / stats.appendContentCalls).toFixed(2)
        : 0;

    console.log("=== ChatMessage Performance Stats ===");
    console.log(`Append content calls: ${stats.appendContentCalls}`);
    console.log(`Total content length: ${stats.totalContentLength} chars`);
    console.log(`Avg append time: ${avgAppendTime}ms`);
    console.log(`Total markdown parse time: ${stats.markdownParseTime.toFixed(2)}ms`);
    console.log(`Total highlight time: ${stats.highlightTime.toFixed(2)}ms`);
    console.log(`Total DOM rebuild time: ${stats.domRebuildTime.toFixed(2)}ms`);
    console.log(
      `Total render time: ${(stats.markdownParseTime + stats.highlightTime + stats.domRebuildTime).toFixed(2)}ms`,
    );
    console.log("=====================================");

    return stats;
  }
}

// Register the custom element
customElements.define("chat-message", ChatMessage);

// Global helper to get stats for the last assistant message
window.getLastMessagePerfStats = () => {
  const messages = document.querySelectorAll('chat-message[role="assistant"]');
  if (messages.length === 0) {
    console.log("No assistant messages found");
    return null;
  }
  const lastMessage = messages[messages.length - 1];
  return lastMessage.printPerfStats();
};
