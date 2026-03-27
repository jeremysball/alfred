/**
 * Message Navigation
 *
 * Keyboard navigation between messages using arrow keys.
 * Works with the KeyboardManager context system.
 */

class MessageNavigator {
  constructor() {
    this.messageSelector = '.message';
  }

  /**
   * Get all message elements
   * @returns {HTMLElement[]}
   * @private
   */
  getMessages() {
    return Array.from(document.querySelectorAll(this.messageSelector));
  }

  /**
   * Get the currently focused message element
   * @returns {HTMLElement|null}
   * @private
   */
  getFocusedMessage() {
    const activeElement = document.activeElement;
    if (!activeElement) return null;

    // Check if active element is a message
    if (activeElement.classList.contains('message')) {
      return activeElement;
    }

    // Check if active element is inside a message
    return activeElement.closest('.message');
  }

  /**
   * Get index of message in the list
   * @param {HTMLElement} message
   * @returns {number}
   * @private
   */
  getMessageIndex(message) {
    const messages = this.getMessages();
    return messages.indexOf(message);
  }

  /**
   * Focus a message by index
   * @param {number} index
   * @returns {boolean} True if message was focused
   * @private
   */
  focusMessageAtIndex(index) {
    const messages = this.getMessages();

    if (index < 0 || index >= messages.length) {
      return false;
    }

    messages[index].focus();
    messages[index].scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    return true;
  }

  /**
   * Navigate to previous message
   * @returns {boolean} True if navigation occurred
   */
  previous() {
    const focused = this.getFocusedMessage();
    if (!focused) return false;

    const currentIndex = this.getMessageIndex(focused);
    if (currentIndex === -1) return false;

    // Wrap to end if at beginning
    const newIndex = currentIndex === 0
      ? this.getMessages().length - 1
      : currentIndex - 1;

    return this.focusMessageAtIndex(newIndex);
  }

  /**
   * Navigate to next message
   * @returns {boolean} True if navigation occurred
   */
  next() {
    const focused = this.getFocusedMessage();
    if (!focused) return false;

    const currentIndex = this.getMessageIndex(focused);
    if (currentIndex === -1) return false;

    const messages = this.getMessages();

    // Wrap to start if at end
    const newIndex = currentIndex === messages.length - 1
      ? 0
      : currentIndex + 1;

    return this.focusMessageAtIndex(newIndex);
  }

  /**
   * Navigate to first message
   * @returns {boolean} True if navigation occurred
   */
  first() {
    const messages = this.getMessages();
    if (messages.length === 0) return false;

    return this.focusMessageAtIndex(0);
  }

  /**
   * Navigate to last message
   * @returns {boolean} True if navigation occurred
   */
  last() {
    const messages = this.getMessages();
    if (messages.length === 0) return false;

    return this.focusMessageAtIndex(messages.length - 1);
  }

  /**
   * Make messages focusable by adding tabindex
   * Call this after new messages are added to DOM
   */
  makeMessagesFocusable() {
    const messages = this.getMessages();
    messages.forEach((msg, index) => {
      if (!msg.hasAttribute('tabindex')) {
        msg.setAttribute('tabindex', '0');
        msg.setAttribute('data-message-index', index.toString());
      }

      // Add focus styles if not present
      if (!msg.classList.contains('message-focusable')) {
        msg.classList.add('message-focusable');
      }
    });
  }
}

// Export for CommonJS
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { MessageNavigator };
}

// Export for browser
if (typeof window !== 'undefined') {
  window.MessageNavigator = MessageNavigator;
}
