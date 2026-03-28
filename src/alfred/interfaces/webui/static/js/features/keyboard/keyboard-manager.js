/**
 * Keyboard Manager
 *
 * Global keyboard listener that handles registered shortcuts
 * with support for modifier keys and context awareness.
 */

import { getAllFlat } from "./shortcuts.js";

class KeyboardManager {
  constructor() {
    this.enabled = true;
    this.handleKeydown = this.handleKeydown.bind(this);

    // Start listening
    this.attachListeners();
  }

  /**
   * Attach global keyboard listeners
   * @private
   */
  attachListeners() {
    document.addEventListener("keydown", this.handleKeydown);
  }

  /**
   * Detach global keyboard listeners
   */
  detachListeners() {
    document.removeEventListener("keydown", this.handleKeydown);
  }

  /**
   * Get current context based on focused element
   * @returns {string} 'global', 'input-focused', or 'message-focused'
   * @private
   */
  getCurrentContext() {
    const activeElement = document.activeElement;

    if (!activeElement) return "global";

    // Check if focused on input/textarea
    if (
      activeElement.tagName === "INPUT" ||
      activeElement.tagName === "TEXTAREA" ||
      activeElement.contentEditable === "true"
    ) {
      return "input-focused";
    }

    // Check if focused on a message element
    if (activeElement.closest(".message") || activeElement.classList.contains("message")) {
      return "message-focused";
    }

    return "global";
  }

  /**
   * Check if a shortcut matches the key event
   * @param {Shortcut} shortcut
   * @param {KeyboardEvent} e
   * @returns {boolean}
   * @private
   */
  matchesShortcut(shortcut, e) {
    // Check key
    const keyMatches =
      e.key.toLowerCase() === shortcut.key || e.code.toLowerCase() === shortcut.key;

    if (!keyMatches) return false;

    // Check modifiers
    if (shortcut.ctrl !== e.ctrlKey) return false;
    if (shortcut.shift !== e.shiftKey) return false;
    if (shortcut.alt !== e.altKey) return false;
    if (shortcut.meta !== e.metaKey) return false;

    return true;
  }

  /**
   * Handle keyboard events
   * @param {KeyboardEvent} e
   * @private
   */
  handleKeydown(e) {
    if (!this.enabled) return;

    const shortcuts = getAllFlat ? getAllFlat() : [];
    const currentContext = this.getCurrentContext();

    for (const shortcut of shortcuts) {
      // Check if shortcut matches context
      if (shortcut.context !== "global" && shortcut.context !== currentContext) {
        continue;
      }

      // Check if key combination matches
      if (this.matchesShortcut(shortcut, e)) {
        e.preventDefault();
        shortcut.action(e);
        return;
      }
    }
  }

  /**
   * Enable keyboard handling
   */
  enable() {
    this.enabled = true;
  }

  /**
   * Disable keyboard handling
   */
  disable() {
    this.enabled = false;
  }

  /**
   * Destroy the manager
   */
  destroy() {
    this.detachListeners();
  }
}

// Export for ESM and browser
export { KeyboardManager };

if (typeof window !== "undefined") {
  window.KeyboardManager = KeyboardManager;
}
