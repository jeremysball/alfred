/**
 * Typing indicator component
 * Shows animated bouncing dots when someone is typing
 */

export class TypingIndicator {
  /**
   * Create a typing indicator element
   * @returns {HTMLElement} The indicator element
   */
  static create() {
    const indicator = document.createElement("div");
    indicator.className = "typing-indicator";
    indicator.setAttribute("role", "status");
    indicator.setAttribute("aria-label", "Typing");

    // Create 3 bouncing dots
    for (let i = 0; i < 3; i++) {
      const dot = document.createElement("span");
      dot.className = "typing-indicator__dot";
      indicator.appendChild(dot);
    }

    // Visually hidden text for screen readers
    const srText = document.createElement("span");
    srText.className = "sr-only";
    srText.textContent = "Assistant is typing...";
    indicator.appendChild(srText);

    return indicator;
  }

  /**
   * Show typing indicator in a container
   * @param {HTMLElement} container - Container to append indicator to
   * @returns {HTMLElement} The indicator element
   */
  static show(container) {
    // Remove existing indicator
    TypingIndicator.hide(container);

    const indicator = TypingIndicator.create();
    container.appendChild(indicator);

    return indicator;
  }

  /**
   * Hide typing indicator from container
   * @param {HTMLElement} container - Container containing indicator
   */
  static hide(container) {
    const existing = container.querySelector(".typing-indicator");
    if (existing) {
      existing.remove();
    }
  }

  /**
   * Check if indicator is currently shown
   * @param {HTMLElement} container - Container to check
   * @returns {boolean}
   */
  static isVisible(container) {
    return container.querySelector(".typing-indicator") !== null;
  }
}
