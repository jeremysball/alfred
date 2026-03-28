/**
 * Quick Session Switcher
 * Ctrl+Tab to open, shows recent sessions with fuzzy search
 * Milestone 9 Phase 2
 */

/**
 * QuickSwitcher - Modal for rapidly switching between recent sessions
 * Uses singleton pattern for single instance across app
 */
export class QuickSwitcher {
  static instance = null;

  /**
   * @param {Object} options - Configuration options
   * @param {number} options.maxSessions - Maximum sessions to show (default: 10)
   * @param {Function} options.onSelect - Callback when session selected (sessionId) => void
   */
  constructor(options = {}) {
    if (QuickSwitcher.instance) {
      return QuickSwitcher.instance;
    }

    this.maxSessions = options.maxSessions || 10;
    this.onSelect = options.onSelect || this.defaultOnSelect;

    this.sessions = [];
    this.filteredSessions = [];
    this.selectedIndex = 0;
    this.isOpen = false;

    this.overlay = null;
    this.searchInput = null;
    this.resultsList = null;
    this.counterEl = null;

    this.boundHandleKeydown = this.handleKeydown.bind(this);
    this.boundHandleInput = this.handleInput.bind(this);
    this.boundHandleClickOutside = this.handleClickOutside.bind(this);

    this.init();
    QuickSwitcher.instance = this;
  }

  static getInstance(options) {
    if (!QuickSwitcher.instance) {
      QuickSwitcher.instance = new QuickSwitcher(options);
    }
    return QuickSwitcher.instance;
  }

  init() {
    this.createDOM();
    this.attachEventListeners();
    this.loadSessions();
  }

  createDOM() {
    // Create overlay container
    this.overlay = document.createElement("div");
    this.overlay.id = "quick-switcher";
    this.overlay.className = "search-overlay hidden";
    this.overlay.setAttribute("role", "dialog");
    this.overlay.setAttribute("aria-label", "Quick Session Switcher");

    // Create search container
    const container = document.createElement("div");
    container.className = "search-container";

    // Create search input
    this.searchInput = document.createElement("input");
    this.searchInput.type = "text";
    this.searchInput.className = "search-input";
    this.searchInput.placeholder = "Switch to session...";
    this.searchInput.setAttribute("autocomplete", "off");
    this.searchInput.setAttribute("aria-label", "Search sessions");

    // Create counter
    this.counterEl = document.createElement("div");
    this.counterEl.className = "search-counter";
    this.counterEl.textContent = "0 sessions";

    // Create results list
    this.resultsList = document.createElement("div");
    this.resultsList.className = "search-results";
    this.resultsList.setAttribute("role", "listbox");

    // Create shortcuts hint
    const shortcuts = document.createElement("div");
    shortcuts.className = "search-shortcuts";
    shortcuts.innerHTML = `
      <span>↑↓ Navigate</span>
      <span>Enter Select</span>
      <span>Esc Close</span>
    `;

    // Assemble
    container.appendChild(this.searchInput);
    container.appendChild(this.counterEl);
    container.appendChild(this.resultsList);
    container.appendChild(shortcuts);
    this.overlay.appendChild(container);

    document.body.appendChild(this.overlay);
  }

  attachEventListeners() {
    this.searchInput.addEventListener("input", this.boundHandleInput);
    document.addEventListener("click", this.boundHandleClickOutside);
  }

  handleKeydown(e) {
    if (!this.isOpen) return;

    switch (e.key) {
      case "Escape":
        e.preventDefault();
        this.close();
        break;
      case "Enter":
        e.preventDefault();
        this.select();
        break;
      case "ArrowDown":
        e.preventDefault();
        this.navigate("next");
        break;
      case "ArrowUp":
        e.preventDefault();
        this.navigate("previous");
        break;
      case "Tab":
        // Prevent tab from moving focus
        e.preventDefault();
        this.navigate(e.shiftKey ? "previous" : "next");
        break;
    }
  }

  handleInput(e) {
    const query = e.target.value;
    this.filter(query);
  }

  handleClickOutside(e) {
    if (!this.isOpen) return;
    if (!this.overlay.contains(e.target)) {
      this.close();
    }
  }

  /**
   * Open the quick switcher modal
   */
  open() {
    if (this.isOpen) return;

    this.loadSessions();
    this.isOpen = true;
    this.overlay.classList.remove("hidden");
    this.searchInput.value = "";
    this.searchInput.focus();
    this.selectedIndex = 0;
    this.filter("");

    // Add keyboard listener
    document.addEventListener("keydown", this.boundHandleKeydown);

    // Trigger custom event
    this.overlay.dispatchEvent(new CustomEvent("quickswitcher:open"));
  }

  /**
   * Close the quick switcher modal
   */
  close() {
    if (!this.isOpen) return;

    this.isOpen = false;
    this.overlay.classList.add("hidden");
    this.searchInput.blur();

    // Remove keyboard listener
    document.removeEventListener("keydown", this.boundHandleKeydown);

    // Trigger custom event
    this.overlay.dispatchEvent(new CustomEvent("quickswitcher:close"));
  }

  /**
   * Filter sessions by query using simple fuzzy matching
   * @param {string} query - Search query
   */
  filter(query) {
    const normalizedQuery = query.toLowerCase().trim();

    if (!normalizedQuery) {
      this.filteredSessions = [...this.sessions];
    } else {
      this.filteredSessions = this.sessions.filter((session) =>
        this.fuzzyMatch(normalizedQuery, session.name.toLowerCase()),
      );
    }

    this.selectedIndex = 0;
    this.renderResults();
    this.updateCounter();
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
    if (this.filteredSessions.length === 0) return;

    if (direction === "next") {
      this.selectedIndex = (this.selectedIndex + 1) % this.filteredSessions.length;
    } else {
      this.selectedIndex =
        (this.selectedIndex - 1 + this.filteredSessions.length) % this.filteredSessions.length;
    }

    this.renderResults();
    this.scrollSelectedIntoView();
  }

  /**
   * Select the currently highlighted session
   */
  select() {
    if (this.filteredSessions.length === 0) return;

    const session = this.filteredSessions[this.selectedIndex];
    this.onSelect(session.id);
    this.close();
  }

  /**
   * Render the results list
   */
  renderResults() {
    this.resultsList.innerHTML = "";

    if (this.filteredSessions.length === 0) {
      const emptyMsg = document.createElement("div");
      emptyMsg.className = "search-empty";
      emptyMsg.textContent = "No sessions found";
      this.resultsList.appendChild(emptyMsg);
      return;
    }

    this.filteredSessions.forEach((session, index) => {
      const item = document.createElement("div");
      item.className = "search-result-item";
      item.setAttribute("role", "option");
      item.setAttribute("aria-selected", index === this.selectedIndex ? "true" : "false");

      if (index === this.selectedIndex) {
        item.classList.add("selected");
      }

      const timeAgo = this.formatTimeAgo(session.timestamp);

      item.innerHTML = `
        <span class="session-name">${this.escapeHtml(session.name)}</span>
        <span class="session-time">${timeAgo}</span>
      `;

      item.addEventListener("click", () => {
        this.selectedIndex = index;
        this.select();
      });

      this.resultsList.appendChild(item);
    });
  }

  /**
   * Scroll the selected item into view
   */
  scrollSelectedIntoView() {
    const selected = this.resultsList.querySelector(".selected");
    if (selected) {
      selected.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  }

  /**
   * Update the counter display
   */
  updateCounter() {
    const count = this.filteredSessions.length;
    const _total = this.sessions.length;
    this.counterEl.textContent = `${count} session${count !== 1 ? "s" : ""}`;
  }

  /**
   * Load sessions from localStorage
   */
  loadSessions() {
    try {
      const stored = localStorage.getItem("alfred_recent_sessions");
      if (stored) {
        this.sessions = JSON.parse(stored);
      } else {
        this.sessions = [];
      }
    } catch (e) {
      console.error("[QuickSwitcher] Failed to load sessions:", e);
      this.sessions = [];
    }
  }

  /**
   * Save sessions to localStorage
   */
  saveSessions() {
    try {
      localStorage.setItem(
        "alfred_recent_sessions",
        JSON.stringify(this.sessions.slice(0, this.maxSessions)),
      );
    } catch (e) {
      console.error("[QuickSwitcher] Failed to save sessions:", e);
    }
  }

  /**
   * Add or update a session in the recent list
   * @param {string} id - Session ID
   * @param {string} name - Session name
   */
  trackSession(id, name) {
    // Remove existing entry if present
    this.sessions = this.sessions.filter((s) => s.id !== id);

    // Add to front
    this.sessions.unshift({
      id,
      name: name || `Session ${id}`,
      timestamp: Date.now(),
    });

    // Trim to max
    this.sessions = this.sessions.slice(0, this.maxSessions);

    this.saveSessions();
  }

  /**
   * Format timestamp as relative time
   * @param {number} timestamp - Unix timestamp in milliseconds
   * @returns {string} - Relative time string
   */
  formatTimeAgo(timestamp) {
    const seconds = Math.floor((Date.now() - timestamp) / 1000);

    if (seconds < 60) return "just now";
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
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
   * Default onSelect handler - sends /resume command via WebSocket
   * @param {string} sessionId - Selected session ID
   */
  defaultOnSelect(sessionId) {
    const wsClient = window.alfredWebSocketClient;
    if (wsClient && typeof wsClient.sendCommand === "function") {
      wsClient.sendCommand(`/resume ${sessionId}`);
    } else {
      console.warn("[QuickSwitcher] WebSocket client not available");
    }
  }

  /**
   * Destroy the instance and clean up
   */
  destroy() {
    document.removeEventListener("keydown", this.boundHandleKeydown);
    document.removeEventListener("click", this.boundHandleClickOutside);

    if (this.overlay?.parentNode) {
      this.overlay.parentNode.removeChild(this.overlay);
    }

    QuickSwitcher.instance = null;
  }
}

/**
 * Initialize the Quick Session Switcher
 * @param {Object} options - Configuration options passed to QuickSwitcher
 * @returns {QuickSwitcher} - The singleton instance
 */
export function initializeQuickSwitcher(options = {}) {
  const switcher = QuickSwitcher.getInstance(options);

  // Register Ctrl+Tab shortcut
  document.addEventListener("keydown", (e) => {
    // Ctrl+Tab (but not Ctrl+Shift+Tab to avoid browser conflict)
    if (e.ctrlKey && e.key === "Tab" && !e.shiftKey) {
      e.preventDefault();
      switcher.open();
    }
  });

  // Hook into session changes to track them
  hookSessionTracking(switcher);

  console.log("[QuickSwitcher] Initialized (Ctrl+Tab)");
  return switcher;
}

/**
 * Hook into session changes to track recent sessions
 * @param {QuickSwitcher} switcher - QuickSwitcher instance
 */
function hookSessionTracking(switcher) {
  // Track when user sends /new or /resume commands
  const originalSendCommand = window.alfredWebSocketClient?.sendCommand;

  if (originalSendCommand) {
    window.alfredWebSocketClient.sendCommand = function (command, ...args) {
      const cmd = command.trim().toLowerCase();

      // Track /new command
      if (cmd === "/new") {
        // New session created - will need to get ID from response
        // For now, we rely on /resume to track
      }

      // Track /resume command
      if (cmd.startsWith("/resume")) {
        const parts = command.split(/\s+/);
        if (parts.length >= 2) {
          const sessionId = parts[1];
          // Get current session name from UI or use ID as fallback
          const sessionName = getCurrentSessionName() || `Session ${sessionId}`;
          switcher.trackSession(sessionId, sessionName);
        }
      }

      return originalSendCommand.call(this, command, ...args);
    };
  }

  // Also track when session is loaded via URL or other means
  // by monitoring the session ID in the UI
  monitorSessionChanges(switcher);
}

/**
 * Get the current session name from the UI
 * @returns {string|null} - Session name or null
 */
function getCurrentSessionName() {
  // Try to find session name in UI
  const sessionHeader = document.querySelector(
    ".session-header, .chat-header, [data-session-name]",
  );
  if (sessionHeader) {
    return sessionHeader.textContent.trim();
  }
  return null;
}

/**
 * Monitor for session ID changes to track sessions
 * @param {QuickSwitcher} switcher - QuickSwitcher instance
 */
function monitorSessionChanges(switcher) {
  // Check for session ID in URL or data attributes
  const checkSession = () => {
    const urlMatch = window.location.pathname.match(/\/session\/([^/]+)/);
    const sessionId = urlMatch ? urlMatch[1] : null;

    if (sessionId && sessionId !== switcher._lastSessionId) {
      switcher._lastSessionId = sessionId;
      const sessionName = getCurrentSessionName() || `Session ${sessionId}`;
      switcher.trackSession(sessionId, sessionName);
    }
  };

  // Check on load and periodically
  checkSession();
  setInterval(checkSession, 5000);
}
