/**
 * Swipe-to-Reply Feature
 *
 * Enables users to swipe right on a message to initiate a reply.
 * Provides visual feedback during swipe with haptic feedback support.
 *
 * Usage:
 *   const swipeReply = new SwipeToReply({
 *     threshold: 80,
 *     onReply: (messageId) => composer.quoteMessage(messageId)
 *   });
 *   swipeReply.attachToAllMessages(messageContainer);
 *
 * Phase 2: Touch Gesture Support - Swipe-to-Reply
 */

import { SwipeDetector } from './swipe-detector.js';

class SwipeToReply {
  constructor(options = {}) {
    this.threshold = options.threshold || 80;
    this.direction = options.direction || 'right';
    this.onReply = options.onReply || (() => {});
    this.enableHaptic = options.enableHaptic !== false; // Default true
    this.enableVisualFeedback = options.enableVisualFeedback !== false; // Default true

    // State
    this._detectors = new Map();
    this._mutationObserver = null;
    this._activeSwipe = null;

    // Constants
    this.SWIPE_ICON_THRESHOLD = 20; // Show icon after 20px
    this.MAX_SWIPE_DISTANCE = 120; // Cap visual movement at 120px
  }

  /**
   * Attach swipe-to-reply to a single message element
   * @param {HTMLElement} element - The message element
   * @param {string} messageId - Unique identifier for the message
   * @returns {boolean} Success status
   */
  attachToMessage(element, messageId) {
    if (!element || !(element instanceof HTMLElement)) {
      console.error('SwipeToReply: Invalid element provided');
      return false;
    }

    // Detach existing if already attached
    this.detachFromMessage(messageId);

    // Create SwipeDetector for this message
    const detector = new SwipeDetector({
      threshold: this.threshold,
      direction: 'horizontal',
      edgeMargin: 0, // Allow swipe from anywhere on message
      onSwipeStart: () => this._handleSwipeStart(element, messageId),
      onSwipeMove: (deltaX, deltaY) => this._handleSwipeMove(element, deltaX, messageId),
      onSwipeEnd: (result) => this._handleSwipeEnd(element, result, messageId)
    });

    detector.attachToElement(element);
    this._detectors.set(messageId, { detector, element });

    return true;
  }

  /**
   * Detach swipe detection from a message
   * @param {string} messageId - The message ID to detach
   */
  detachFromMessage(messageId) {
    const entry = this._detectors.get(messageId);
    if (entry) {
      entry.detector.destroy();
      this._resetVisualState(entry.element);
      this._detectors.delete(messageId);
    }
  }

  /**
   * Attach to all messages in a container
   * @param {HTMLElement} container - Container with message elements
   * @param {string} selector - CSS selector for message elements
   * @returns {number} Number of messages attached
   */
  attachToAllMessages(container, selector = '[data-message-id]') {
    if (!container || !(container instanceof HTMLElement)) {
      console.error('SwipeToReply: Invalid container provided');
      return 0;
    }

    const messages = container.querySelectorAll(selector);
    let count = 0;

    messages.forEach((element) => {
      const messageId = element.dataset.messageId;
      if (messageId) {
        if (this.attachToMessage(element, messageId)) {
          count++;
        }
      }
    });

    // Set up mutation observer for dynamic messages
    this._setupMutationObserver(container, selector);

    return count;
  }

  /**
   * Set up mutation observer to handle dynamically added messages
   * @param {HTMLElement} container - The message container
   * @param {string} selector - CSS selector for messages
   */
  _setupMutationObserver(container, selector) {
    if (this._mutationObserver) {
      this._mutationObserver.disconnect();
    }

    this._mutationObserver = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        mutation.addedNodes.forEach((node) => {
          if (node.nodeType === Node.ELEMENT_NODE) {
            // Check if the added node is a message
            if (node.matches && node.matches(selector)) {
              const messageId = node.dataset.messageId;
              if (messageId) {
                this.attachToMessage(node, messageId);
              }
            }

            // Check for messages within the added node
            if (node.querySelectorAll) {
              const nestedMessages = node.querySelectorAll(selector);
              nestedMessages.forEach((element) => {
                const messageId = element.dataset.messageId;
                if (messageId) {
                  this.attachToMessage(element, messageId);
                }
              });
            }
          }
        });
      });
    });

    this._mutationObserver.observe(container, {
      childList: true,
      subtree: true
    });
  }

  /**
   * Handle swipe start
   * @param {HTMLElement} element - The message element
   * @param {string} messageId - The message ID
   */
  _handleSwipeStart(element, messageId) {
    this._activeSwipe = { element, messageId, startTime: Date.now() };
    element.classList.add('swiping');

    if (this.enableHaptic) {
      this._triggerHaptic();
    }
  }

  /**
   * Handle swipe move
   * @param {HTMLElement} element - The message element
   * @param {number} deltaX - Horizontal movement
   * @param {string} messageId - The message ID
   */
  _handleSwipeMove(element, deltaX, messageId) {
    if (!this._activeSwipe) return;

    // Only allow right swipes for reply (positive deltaX)
    if (this.direction === 'right' && deltaX < 0) {
      deltaX = 0;
    }

    // Cap the visual movement
    const visualDistance = Math.min(deltaX, this.MAX_SWIPE_DISTANCE);

    // Apply visual feedback
    if (this.enableVisualFeedback) {
      this._applyVisualFeedback(element, visualDistance);
    }
  }

  /**
   * Handle swipe end
   * @param {HTMLElement} element - The message element
   * @param {Object} result - Swipe result from detector
   * @param {string} messageId - The message ID
   * @returns {boolean} Whether reply was triggered
   */
  _handleSwipeEnd(element, result, messageId) {
    this._activeSwipe = null;
    element.classList.remove('swiping');

    const isRightSwipe = result.direction === 'right';
    const isAboveThreshold = result.distance >= this.threshold;

    if (isRightSwipe && isAboveThreshold) {
      // Trigger reply
      this._triggerReply(messageId);
      this._resetVisualState(element);
      return true;
    } else {
      // Snap back
      this._snapBack(element);
      return false;
    }
  }

  /**
   * Apply visual feedback during swipe
   * @param {HTMLElement} element - The message element
   * @param {number} distance - Swipe distance in pixels
   */
  _applyVisualFeedback(element, distance) {
    // Use transform for smooth, GPU-accelerated movement
    element.style.transform = `translateX(${distance}px)`;
    element.style.transition = 'none'; // No transition during drag

    // Show reply icon when past threshold
    if (distance >= this.SWIPE_ICON_THRESHOLD) {
      this._showReplyIcon(element, distance);
    } else {
      this._hideReplyIcon(element);
    }

    // Scale opacity based on distance (subtle fade effect)
    const progress = this._calculateProgress(distance);
    element.style.opacity = String(1 - (progress * 0.15)); // Fade to 85%
  }

  /**
   * Show reply icon overlay
   * @param {HTMLElement} element - The message element
   * @param {number} distance - Current swipe distance
   */
  _showReplyIcon(element, distance) {
    let icon = element.querySelector('.swipe-reply-icon');

    if (!icon) {
      icon = document.createElement('div');
      icon.className = 'swipe-reply-icon';
      icon.innerHTML = '↩️';
      icon.style.cssText = `
        position: absolute;
        left: 10px;
        top: 50%;
        transform: translateY(-50%);
        opacity: 0;
        transition: opacity 0.15s ease;
        pointer-events: none;
        font-size: 20px;
      `;
      element.style.position = 'relative';
      element.appendChild(icon);
    }

    // Fade in icon based on progress
    const progress = this._calculateProgress(distance);
    icon.style.opacity = String(progress);
  }

  /**
   * Hide reply icon
   * @param {HTMLElement} element - The message element
   */
  _hideReplyIcon(element) {
    const icon = element.querySelector('.swipe-reply-icon');
    if (icon) {
      icon.style.opacity = '0';
    }
  }

  /**
   * Calculate swipe progress (0-1)
   * @param {number} distance - Current distance
   * @returns {number} Progress ratio
   */
  _calculateProgress(distance) {
    return Math.min(Math.max(distance / this.threshold, 0), 1);
  }

  /**
   * Snap message back to original position
   * @param {HTMLElement} element - The message element
   */
  _snapBack(element) {
    element.style.transition = 'transform 0.3s cubic-bezier(0.4, 0.0, 0.2, 1), opacity 0.3s ease';
    element.style.transform = 'translateX(0)';
    element.style.opacity = '1';

    // Hide icon
    this._hideReplyIcon(element);

    // Clean up after animation
    setTimeout(() => {
      this._resetVisualState(element);
    }, 300);
  }

  /**
   * Reset visual state completely
   * @param {HTMLElement} element - The message element
   */
  _resetVisualState(element) {
    element.style.transform = '';
    element.style.transition = '';
    element.style.opacity = '';

    // Remove icon
    const icon = element.querySelector('.swipe-reply-icon');
    if (icon) {
      icon.remove();
    }
  }

  /**
   * Trigger haptic feedback
   */
  _triggerHaptic() {
    if (!this.enableHaptic) return;

    if (navigator.vibrate) {
      // Short, light vibration for feedback
      navigator.vibrate(10);
    }
  }

  /**
   * Trigger reply callback
   * @param {string} messageId - The message being replied to
   */
  _triggerReply(messageId) {
    if (this.enableHaptic) {
      // Stronger feedback for successful swipe
      if (navigator.vibrate) {
        navigator.vibrate([20, 30, 20]);
      }
    }

    this.onReply(messageId);
  }

  /**
   * Detach all swipe detectors and clean up
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
      this._resetVisualState(entry.element);
    });
    this._detectors.clear();

    this._activeSwipe = null;
  }
}

// Export for ESM and browser usage
export { SwipeToReply };

if (typeof window !== 'undefined') {
  window.SwipeToReply = SwipeToReply;
}
