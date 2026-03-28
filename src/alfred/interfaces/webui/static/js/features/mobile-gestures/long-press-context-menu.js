/**
 * Long Press Context Menu
 *
 * Enables long press on messages to open the context menu.
 * Integrates LongPressDetector with the existing context menu system.
 *
 * Usage:
 *   const longPressMenu = new LongPressContextMenu({
 *     threshold: 500,
 *     showContextMenu: (element, x, y) => MessageContextMenu.showMessageMenu(element, x, y)
 *   });
 *   longPressMenu.attachToAllMessages(messageContainer);
 *
 * Phase 3: Touch Gesture Support - Long Press Context Menu
 */

import { LongPressDetector } from "./long-press-detector.js";

class LongPressContextMenu {
  constructor(options = {}) {
    // Configuration
    this.threshold = options.threshold || 500; // ms to trigger
    this.movementTolerance = options.movementTolerance || 10;
    this.enableHaptic = options.enableHaptic !== false;
    this.enableVisualFeedback = options.enableVisualFeedback !== false;

    // Context menu callback
    // Should be a function: (element, x, y) => void
    this.showContextMenu = options.showContextMenu || null;

    // State
    this._detectors = new Map(); // messageId -> detector
    this._mutationObserver = null;
    this._activeElement = null;

    // Exclude selectors (elements that should not trigger long press)
    this.excludeSelectors = options.excludeSelectors || [
      "a",
      "button",
      "input",
      "textarea",
      "select",
      "[contenteditable]",
    ];
  }

  /**
   * Attach long press to a single element
   * @param {HTMLElement} element - The element to attach to
   * @param {string} elementId - Unique identifier for the element
   * @returns {boolean} Success status
   */
  attachToElement(element, elementId) {
    if (!element || !(element instanceof HTMLElement)) {
      console.error("LongPressContextMenu: Invalid element provided");
      return false;
    }

    // Detach existing if already attached
    this.detachFromElement(elementId);

    // Create LongPressDetector for this element
    const detector = new LongPressDetector({
      threshold: this.threshold,
      movementTolerance: this.movementTolerance,
      enableHaptic: this.enableHaptic,
      enableVisualFeedback: this.enableVisualFeedback,
      onLongPress: (el) => this._handleLongPress(el, elementId),
      onPressStart: (el) => this._handlePressStart(el),
      onPressCancel: (el) => this._handlePressCancel(el),
    });

    detector.attachToElement(element);
    this._detectors.set(elementId, { detector, element });

    return true;
  }

  /**
   * Detach long press detection from an element
   * @param {string} elementId - The element ID to detach
   */
  detachFromElement(elementId) {
    const entry = this._detectors.get(elementId);
    if (entry) {
      entry.detector.destroy();
      this._detectors.delete(elementId);
    }
  }

  /**
   * Attach to all elements in a container
   * @param {HTMLElement} container - Container with elements
   * @param {string} selector - CSS selector for elements
   * @param {string} idAttribute - Data attribute for element IDs
   * @returns {number} Number of elements attached
   */
  attachToAllElements(container, selector = "[data-message-id]", idAttribute = "messageId") {
    if (!container || !(container instanceof HTMLElement)) {
      console.error("LongPressContextMenu: Invalid container provided");
      return 0;
    }

    const elements = container.querySelectorAll(selector);
    let count = 0;

    elements.forEach((element) => {
      const elementId = element.dataset[idAttribute];
      if (elementId) {
        if (this.attachToElement(element, elementId)) {
          count++;
        }
      }
    });

    // Set up mutation observer for dynamic elements
    this._setupMutationObserver(container, selector, idAttribute);

    return count;
  }

  /**
   * Convenience method for messages (matches MessageContextMenu pattern)
   * @param {HTMLElement} container - Message container
   * @returns {number} Number of messages attached
   */
  attachToAllMessages(container) {
    return this.attachToAllElements(container, ".message, [data-message-id]", "messageId");
  }

  /**
   * Set up mutation observer to handle dynamically added elements
   * @param {HTMLElement} container - The container
   * @param {string} selector - CSS selector
   * @param {string} idAttribute - Data attribute name
   */
  _setupMutationObserver(container, selector, idAttribute) {
    if (this._mutationObserver) {
      this._mutationObserver.disconnect();
    }

    this._mutationObserver = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        mutation.addedNodes.forEach((node) => {
          if (node.nodeType === Node.ELEMENT_NODE) {
            // Check if the added node matches selector
            if (node.matches?.(selector)) {
              const elementId = node.dataset[idAttribute];
              if (elementId) {
                this.attachToElement(node, elementId);
              }
            }

            // Check for nested elements
            if (node.querySelectorAll) {
              const nestedElements = node.querySelectorAll(selector);
              nestedElements.forEach((element) => {
                const elementId = element.dataset[idAttribute];
                if (elementId) {
                  this.attachToElement(element, elementId);
                }
              });
            }
          }
        });
      });
    });

    this._mutationObserver.observe(container, {
      childList: true,
      subtree: true,
    });
  }

  /**
   * Handle long press activation
   * @param {HTMLElement} element - The pressed element
   * @param {string} elementId - Element identifier
   */
  _handleLongPress(element, _elementId) {
    // Check if clicking on excluded element
    if (this._isExcludedElement(element)) {
      return;
    }

    // Calculate center position for menu
    const rect = element.getBoundingClientRect();
    const x = rect.left + rect.width / 2;
    const y = rect.top + rect.height / 2;

    // Show context menu
    if (this.showContextMenu) {
      this.showContextMenu(element, x, y);
    } else if (window.MessageContextMenu?.showMessageMenu) {
      // Fallback to global MessageContextMenu
      window.MessageContextMenu.showMessageMenu(element, x, y);
    } else {
      console.warn("LongPressContextMenu: No context menu handler configured");
    }

    this._activeElement = null;
  }

  /**
   * Handle press start
   * @param {HTMLElement} element - The pressed element
   */
  _handlePressStart(element) {
    this._activeElement = element;
  }

  /**
   * Handle press cancel
   * @param {HTMLElement} element - The element
   */
  _handlePressCancel(_element) {
    this._activeElement = null;
  }

  /**
   * Check if element or its children match excluded selectors
   * @param {HTMLElement} element - Element to check
   * @returns {boolean}
   */
  _isExcludedElement(element) {
    for (const selector of this.excludeSelectors) {
      if (element.matches(selector) || element.closest(selector)) {
        return true;
      }
    }
    return false;
  }

  /**
   * Get the number of attached detectors
   * @returns {number}
   */
  getAttachedCount() {
    return this._detectors.size;
  }

  /**
   * Check if an element is currently being pressed
   * @returns {boolean}
   */
  isPressing() {
    return this._activeElement !== null;
  }

  /**
   * Destroy all detectors and clean up
   */
  destroy() {
    // Disconnect mutation observer
    if (this._mutationObserver) {
      this._mutationObserver.disconnect();
      this._mutationObserver = null;
    }

    // Destroy all detectors
    this._detectors.forEach((entry) => {
      entry.detector.destroy();
    });
    this._detectors.clear();

    this._activeElement = null;
  }
}

// Export for ESM and browser usage
export { LongPressContextMenu };

if (typeof window !== "undefined") {
  window.LongPressContextMenu = LongPressContextMenu;
}
