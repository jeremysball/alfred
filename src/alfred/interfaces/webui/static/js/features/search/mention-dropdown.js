/**
 * @ Mentions - Reference previous messages in composer
 * Milestone 9 Phase 3
 */

/**
 * MentionDropdown - Dropdown for referencing previous messages via @
 * Uses singleton pattern for single instance per composer
 */
export class MentionDropdown {
  static instance = null;

  /**
   * @param {Object} options - Configuration options
   * @param {HTMLElement} options.composer - Text input element (default: #message-input)
   * @param {number} options.maxMessages - Max messages to show (default: 20)
   */
  constructor(options = {}) {
    if (MentionDropdown.instance) {
      return MentionDropdown.instance;
    }

    this.composer = options.composer || document.getElementById("message-input");
    this.maxMessages = options.maxMessages || 20;
    this.triggerChar = "@";

    this.isOpen = false;
    this.query = "";
    this.messages = [];
    this.filteredMessages = [];
    this.selectedIndex = 0;
    this.mentionStartIndex = -1; // Position of @ in composer

    this.dropdown = null;
    this.listEl = null;

    this.boundHandleKeydown = this.handleKeydown.bind(this);
    this.boundHandleInput = this.handleInput.bind(this);
    this.boundHandleBlur = this.handleBlur.bind(this);

    if (this.composer) {
      this.init();
    }

    MentionDropdown.instance = this;
  }

  static getInstance(options) {
    if (!MentionDropdown.instance) {
      MentionDropdown.instance = new MentionDropdown(options);
    }
    return MentionDropdown.instance;
  }

  init() {
    this.createDOM();
    this.attachEventListeners();
  }

  createDOM() {
    // Positioned absolute below cursor
    this.dropdown = document.createElement("div");
    this.dropdown.className = "mention-dropdown hidden";
    this.dropdown.setAttribute("role", "listbox");
    this.dropdown.setAttribute("aria-label", "Message mentions");

    const listContainer = document.createElement("div");
    listContainer.className = "mention-list";
    this.listEl = listContainer;

    const hint = document.createElement("div");
    hint.className = "mention-hint";
    hint.innerHTML = "<span>↑↓ Navigate</span><span>Enter Select</span><span>Esc Close</span>";

    this.dropdown.appendChild(listContainer);
    this.dropdown.appendChild(hint);
    document.body.appendChild(this.dropdown);
  }

  attachEventListeners() {
    this.composer.addEventListener("input", this.boundHandleInput);
    this.composer.addEventListener("keydown", this.boundHandleKeydown);
    this.composer.addEventListener("blur", this.boundHandleBlur);
  }

  handleInput(_e) {
    const cursorPos = this.composer.selectionStart;
    const textBeforeCursor = this.composer.value.slice(0, cursorPos);

    // Check if we're in an @ mention context
    const lastAtIndex = textBeforeCursor.lastIndexOf("@");

    if (lastAtIndex === -1) {
      this.close();
      return;
    }

    // Check if @ is at word boundary (preceded by space or start of string)
    const charBeforeAt = textBeforeCursor[lastAtIndex - 1];
    if (charBeforeAt && !/\s/.test(charBeforeAt)) {
      this.close();
      return;
    }

    // Extract query (text after @ up to cursor)
    this.query = textBeforeCursor.slice(lastAtIndex + 1);

    // Don't trigger if query has spaces (user moved to next word)
    if (this.query.includes(" ")) {
      this.close();
      return;
    }

    // Store the start position of this mention
    this.mentionStartIndex = lastAtIndex;

    if (!this.isOpen) {
      this.open();
    }
    this.filter(this.query);
  }

  handleKeydown(e) {
    if (!this.isOpen) return;

    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        this.navigate("next");
        break;
      case "ArrowUp":
        e.preventDefault();
        this.navigate("previous");
        break;
      case "Enter":
      case "Tab":
        e.preventDefault();
        this.select();
        break;
      case "Escape":
        e.preventDefault();
        this.close();
        break;
    }
  }

  handleBlur() {
    // Delay to allow click on dropdown items
    setTimeout(() => {
      // Only close if focus is not within the dropdown
      if (!this.dropdown.contains(document.activeElement)) {
        this.close();
      }
    }, 200);
  }

  /**
   * Open the mention dropdown
   */
  open() {
    if (this.isOpen) return;

    this.isOpen = true;
    this.dropdown.classList.remove("hidden");
    this.messages = this.extractMessages();
    this.positionDropdown();

    // Dispatch custom event
    this.dropdown.dispatchEvent(new CustomEvent("mention:open"));
  }

  /**
   * Close the mention dropdown
   */
  close() {
    if (!this.isOpen) return;

    this.isOpen = false;
    this.dropdown.classList.add("hidden");
    this.query = "";
    this.filteredMessages = [];
    this.mentionStartIndex = -1;

    // Dispatch custom event
    this.dropdown.dispatchEvent(new CustomEvent("mention:close"));
  }

  /**
   * Filter messages by query using fuzzy matching
   * @param {string} query - Search query
   */
  filter(query) {
    const normalizedQuery = query.toLowerCase().trim();

    if (!normalizedQuery) {
      this.filteredMessages = this.messages.slice(0, this.maxMessages);
    } else {
      this.filteredMessages = this.messages
        .filter((m) => this.fuzzyMatch(normalizedQuery, m.text.toLowerCase()))
        .slice(0, this.maxMessages);
    }

    this.selectedIndex = 0;
    this.render();
  }

  /**
   * Simple fuzzy matching - checks if all characters in query appear in text in order
   * @param {string} query - Lowercase query
   * @param {string} text - Lowercase text to search
   * @returns {boolean} - Whether text matches query
   */
  fuzzyMatch(query, text) {
    let queryIndex = 0;
    for (let i = 0; i < text.length && queryIndex < query.length; i++) {
      if (text[i] === query[queryIndex]) {
        queryIndex++;
      }
    }
    return queryIndex === query.length;
  }

  /**
   * Navigate through results
   * @param {string} direction - 'next' or 'previous'
   */
  navigate(direction) {
    const len = this.filteredMessages.length;
    if (len === 0) return;

    if (direction === "next") {
      this.selectedIndex = (this.selectedIndex + 1) % len;
    } else {
      this.selectedIndex = (this.selectedIndex - 1 + len) % len;
    }

    this.render();
    this.scrollSelectedIntoView();
  }

  /**
   * Select the currently highlighted message
   */
  select() {
    if (this.filteredMessages.length === 0) return;

    const message = this.filteredMessages[this.selectedIndex];
    this.insertMention(message);
    this.close();
  }

  /**
   * Insert mention text into composer
   * @param {Object} message - Message to mention
   */
  insertMention(message) {
    const fullText = this.composer.value;
    const cursorPos = this.composer.selectionStart;

    // Find the @ that triggered this mention
    const textBeforeCursor = fullText.slice(0, cursorPos);
    const lastAtIndex = textBeforeCursor.lastIndexOf("@");

    if (lastAtIndex === -1) return;

    // Build mention text
    const excerpt = message.text.slice(0, 50) + (message.text.length > 50 ? "..." : "");
    const mentionText = `@${message.author}: "${excerpt}" `;

    // Replace @query with mention
    const newText = fullText.slice(0, lastAtIndex) + mentionText + fullText.slice(cursorPos);

    this.composer.value = newText;
    this.composer.focus();

    // Position cursor after mention
    const newCursorPos = lastAtIndex + mentionText.length;
    this.composer.setSelectionRange(newCursorPos, newCursorPos);

    // Trigger input event for any listeners
    this.composer.dispatchEvent(new Event("input", { bubbles: true }));

    // Dispatch custom event
    this.composer.dispatchEvent(
      new CustomEvent("mention:insert", {
        detail: { message, mentionText },
      }),
    );
  }

  /**
   * Extract messages from DOM
   * @returns {Array} - Array of message objects
   */
  extractMessages() {
    // Scan DOM for message elements
    const messageEls = document.querySelectorAll(".message, [data-message-id]");
    const messages = [];
    const seenIds = new Set();

    messageEls.forEach((el) => {
      const id = el.dataset.messageId;
      const textEl = el.querySelector(".message-text, .content, .text, .message-content");
      const authorEl = el.querySelector(".author, .username, .sender, .message-author");

      // Skip if no ID or already seen
      if (!id || seenIds.has(id)) return;
      seenIds.add(id);

      // Skip if no text content
      if (!textEl?.textContent.trim()) return;

      messages.push({
        id,
        text: textEl.textContent.trim(),
        author: authorEl?.textContent.trim() || "Unknown",
        element: el,
      });
    });

    // Reverse to show most recent first
    return messages.reverse();
  }

  /**
   * Position dropdown below cursor in composer
   */
  positionDropdown() {
    // Get composer position
    const composerRect = this.composer.getBoundingClientRect();

    // Calculate position (below composer, aligned left)
    const top = composerRect.bottom + window.scrollY + 5;
    let left = composerRect.left + window.scrollX;

    // Adjust if would go off screen
    const _dropdownRect = this.dropdown.getBoundingClientRect();
    const windowWidth = window.innerWidth;

    if (left + 300 > windowWidth) {
      left = windowWidth - 310;
    }

    this.dropdown.style.top = `${top}px`;
    this.dropdown.style.left = `${left}px`;
  }

  /**
   * Render the dropdown list
   */
  render() {
    if (this.filteredMessages.length === 0) {
      this.listEl.innerHTML = '<div class="mention-empty">No messages found</div>';
      return;
    }

    this.listEl.innerHTML = "";

    this.filteredMessages.forEach((msg, index) => {
      const item = document.createElement("div");
      item.className = "mention-item";
      item.setAttribute("role", "option");
      item.setAttribute("aria-selected", index === this.selectedIndex ? "true" : "false");

      if (index === this.selectedIndex) {
        item.classList.add("selected");
      }

      const authorSpan = document.createElement("span");
      authorSpan.className = "mention-author";
      authorSpan.textContent = msg.author;

      const textSpan = document.createElement("span");
      textSpan.className = "mention-text";
      const excerpt = msg.text.slice(0, 60) + (msg.text.length > 60 ? "..." : "");
      textSpan.textContent = excerpt;

      item.appendChild(authorSpan);
      item.appendChild(textSpan);

      // Click to select
      item.addEventListener("mousedown", (e) => {
        e.preventDefault(); // Prevent blur from closing before click
        this.selectedIndex = index;
        this.select();
      });

      this.listEl.appendChild(item);
    });
  }

  /**
   * Scroll selected item into view
   */
  scrollSelectedIntoView() {
    const selected = this.listEl.querySelector(".selected");
    if (selected) {
      selected.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  }

  /**
   * Escape HTML to prevent XSS
   * @param {string} text - Text to escape
   * @returns {string} - Escaped text
   */
  escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Destroy the instance and clean up
   */
  destroy() {
    this.composer.removeEventListener("input", this.boundHandleInput);
    this.composer.removeEventListener("keydown", this.boundHandleKeydown);
    this.composer.removeEventListener("blur", this.boundHandleBlur);

    if (this.dropdown?.parentNode) {
      this.dropdown.parentNode.removeChild(this.dropdown);
    }

    MentionDropdown.instance = null;
  }
}

/**
 * Initialize @ mentions for a composer element
 * @param {Object} options - Configuration options
 * @returns {MentionDropdown} - The singleton instance
 */
export function initializeMentions(options = {}) {
  const dropdown = MentionDropdown.getInstance(options);
  console.log("[Mentions] @ mentions initialized");
  return dropdown;
}
