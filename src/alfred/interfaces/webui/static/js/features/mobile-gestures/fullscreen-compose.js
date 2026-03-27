/**
 * Fullscreen Compose Modal
 *
 * Mobile fullscreen compose interface triggered by swipe-up gesture.
 * Provides distraction-free writing environment with glassmorphism styling.
 */

/**
 * FullscreenComposeModal - Modal component for fullscreen message composition
 *
 * Opens via swipe-up on composer input, closes via swipe-down, close button, or Escape key.
 * Synchronizes content between compact and fullscreen inputs.
 */
class FullscreenComposeModal {
  /**
   * Create a new FullscreenComposeModal instance
   *
   * @param {Object} options - Configuration options
   * @param {HTMLTextAreaElement} options.compactInput - Reference to compact composer textarea
   * @param {Function} options.onOpen - Callback when modal opens
   * @param {Function} options.onClose - Callback when modal closes
   * @param {Function} options.onSubmit - Callback when message is submitted
   * @param {string} options.placeholder - Placeholder text for fullscreen textarea
   */
  constructor(options = {}) {
    this.compactInput = options.compactInput;
    this.onOpen = typeof options.onOpen === 'function' ? options.onOpen : () => {};
    this.onClose = typeof options.onClose === 'function' ? options.onClose : () => {};
    this.onSubmit = typeof options.onSubmit === 'function' ? options.onSubmit : () => {};
    this.placeholder = options.placeholder || 'Type a message...';

    // DOM element references
    this.element = null;
    this.textarea = null;
    this.closeButton = null;
    this.submitButton = null;
    this.backdrop = null;

    // State
    this.isOpen = false;
    this.isAnimating = false;
    this.swipeDownDetector = null;

    // Bound methods for event listeners
    this._handleKeyDown = this._handleKeyDown.bind(this);
    this._handleSubmit = this._handleSubmit.bind(this);
    this._handleInput = this._handleInput.bind(this);
    this._handleSwipeDown = this._handleSwipeDown.bind(this);
  }

  /**
   * Open the fullscreen compose modal
   */
  open() {
    if (this.isOpen || this.isAnimating) {
      return;
    }

    this.isAnimating = true;

    // Create modal DOM
    this._createModal();

    // Transfer content from compact input
    if (this.compactInput) {
      this.textarea.value = this.compactInput.value;
    }

    // Trigger animation
    requestAnimationFrame(() => {
      this.element.classList.add('is-open');
      this.backdrop.classList.add('is-visible');
    });

    // Focus fullscreen textarea after animation
    setTimeout(() => {
      this.textarea.focus();
      this.isAnimating = false;
      this.isOpen = true;
      this.onOpen();
    }, 50);

    // Add keyboard listener
    document.addEventListener('keydown', this._handleKeyDown);

    // Initialize swipe-down detector
    this._initSwipeDown();
  }

  /**
   * Close the fullscreen compose modal
   * @param {boolean} transferContent - Whether to transfer content back to compact input
   */
  close(transferContent = true) {
    if (!this.isOpen || this.isAnimating) {
      return;
    }

    this.isAnimating = true;

    // Transfer content back to compact input
    if (transferContent && this.compactInput) {
      this.compactInput.value = this.textarea.value;
    }

    // Trigger close animation
    this.element.classList.remove('is-open');
    this.element.classList.add('is-closing');
    this.backdrop.classList.remove('is-visible');

    // Remove after animation completes
    setTimeout(() => {
      this._destroyModal();
      this.isAnimating = false;
      this.isOpen = false;
      this.onClose();

      // Return focus to compact input
      if (this.compactInput) {
        this.compactInput.focus();
      }
    }, 300);

    // Remove keyboard listener
    document.removeEventListener('keydown', this._handleKeyDown);
  }

  /**
   * Submit the message and close
   */
  submit() {
    const content = this.textarea.value.trim();
    if (content) {
      this.onSubmit(content);
      this.textarea.value = '';
      if (this.compactInput) {
        this.compactInput.value = '';
      }
    }
    this.close(false);
  }

  /**
   * Check if modal is currently open
   * @returns {boolean}
   */
  isOpened() {
    return this.isOpen;
  }

  /**
   * Get current content
   * @returns {string}
   */
  getContent() {
    return this.textarea ? this.textarea.value : '';
  }

  /**
   * Set content
   * @param {string} content
   */
  setContent(content) {
    if (this.textarea) {
      this.textarea.value = content;
    }
  }

  /**
   * Destroy the modal and clean up
   */
  destroy() {
    this.close();
    // Additional cleanup if needed
  }

  /**
   * Create the modal DOM structure
   * @private
   */
  _createModal() {
    // Create backdrop
    this.backdrop = document.createElement('div');
    this.backdrop.className = 'fullscreen-compose__backdrop';

    // Create modal container
    this.element = document.createElement('div');
    this.element.className = 'fullscreen-compose';
    this.element.setAttribute('role', 'dialog');
    this.element.setAttribute('aria-modal', 'true');
    this.element.setAttribute('aria-label', 'Fullscreen compose');

    // Create swipe indicator
    const swipeIndicator = document.createElement('div');
    swipeIndicator.className = 'fullscreen-compose__swipe-indicator';
    swipeIndicator.setAttribute('aria-hidden', 'true');

    // Create header with close button
    const header = document.createElement('div');
    header.className = 'fullscreen-compose__header';

    const title = document.createElement('h2');
    title.className = 'fullscreen-compose__title';
    title.textContent = 'New Message';

    this.closeButton = document.createElement('button');
    this.closeButton.className = 'fullscreen-compose__close';
    this.closeButton.setAttribute('aria-label', 'Close fullscreen compose');
    this.closeButton.innerHTML = `
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <line x1="18" y1="6" x2="6" y2="18"></line>
        <line x1="6" y1="6" x2="18" y2="18"></line>
      </svg>
    `;
    this.closeButton.addEventListener('click', () => this.close());

    header.appendChild(title);
    header.appendChild(this.closeButton);

    // Create textarea
    this.textarea = document.createElement('textarea');
    this.textarea.className = 'fullscreen-compose__textarea';
    this.textarea.placeholder = this.placeholder;
    this.textarea.setAttribute('aria-label', 'Message text');
    this.textarea.addEventListener('input', this._handleInput);

    // Create submit button
    this.submitButton = document.createElement('button');
    this.submitButton.className = 'fullscreen-compose__submit';
    this.submitButton.textContent = 'Send';
    this.submitButton.addEventListener('click', this._handleSubmit);

    // Assemble modal
    this.element.appendChild(swipeIndicator);
    this.element.appendChild(header);
    this.element.appendChild(this.textarea);
    this.element.appendChild(this.submitButton);

    // Append to document
    document.body.appendChild(this.backdrop);
    document.body.appendChild(this.element);
  }

  /**
   * Destroy modal DOM elements
   * @private
   */
  _destroyModal() {
    if (this.swipeDownDetector && this.swipeDownDetector.destroy) {
      this.swipeDownDetector.destroy();
      this.swipeDownDetector = null;
    }

    if (this.closeButton) {
      this.closeButton.removeEventListener('click', () => this.close());
      this.closeButton = null;
    }

    if (this.submitButton) {
      this.submitButton.removeEventListener('click', this._handleSubmit);
      this.submitButton = null;
    }

    if (this.textarea) {
      this.textarea.removeEventListener('input', this._handleInput);
      this.textarea = null;
    }

    if (this.element && this.element.parentNode) {
      this.element.parentNode.removeChild(this.element);
      this.element = null;
    }

    if (this.backdrop && this.backdrop.parentNode) {
      this.backdrop.parentNode.removeChild(this.backdrop);
      this.backdrop = null;
    }
  }

  /**
   * Initialize swipe-down detector for closing
   * @private
   */
  _initSwipeDown() {
    // Simple swipe detection without importing SwipeDetector
    // to avoid circular dependencies
    let startY = 0;
    let isTracking = false;
    const threshold = 80;

    const handleTouchStart = (e) => {
      if (e.touches.length === 1) {
        startY = e.touches[0].clientY;
        isTracking = true;
      }
    };

    const handleTouchMove = (e) => {
      if (!isTracking) return;

      const currentY = e.touches[0].clientY;
      const deltaY = currentY - startY;

      // If swiping down
      if (deltaY > 0) {
        // Optional: Add resistance effect here
        if (deltaY > threshold) {
          isTracking = false;
          this._handleSwipeDown();
        }
      }
    };

    const handleTouchEnd = () => {
      isTracking = false;
    };

    this.element.addEventListener('touchstart', handleTouchStart, { passive: true });
    this.element.addEventListener('touchmove', handleTouchMove, { passive: true });
    this.element.addEventListener('touchend', handleTouchEnd, { passive: true });

    this.swipeDownDetector = {
      destroy: () => {
        if (this.element) {
          this.element.removeEventListener('touchstart', handleTouchStart);
          this.element.removeEventListener('touchmove', handleTouchMove);
          this.element.removeEventListener('touchend', handleTouchEnd);
        }
      }
    };
  }

  /**
   * Handle keyboard events (Escape to close)
   * @private
   */
  _handleKeyDown(e) {
    if (e.key === 'Escape') {
      e.preventDefault();
      this.close();
    }

    // Cmd/Ctrl + Enter to submit
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault();
      this.submit();
    }
  }

  /**
   * Handle submit button click
   * @private
   */
  _handleSubmit(e) {
    e.preventDefault();
    this.submit();
  }

  /**
   * Handle textarea input
   * @private
   */
  _handleInput() {
    // Optional: Sync back to compact input in real-time
    // if (this.compactInput) {
    //   this.compactInput.value = this.textarea.value;
    // }
  }

  /**
   * Handle swipe-down gesture
   * @private
   */
  _handleSwipeDown() {
    this.close();
  }
}

/**
 * Factory function to create a swipe-up fullscreen compose setup
 *
 * @param {HTMLTextAreaElement} compactInput - The compact composer textarea
 * @param {Object} options - Options passed to FullscreenComposeModal
 * @returns {Object} Object containing modal and cleanup function
 */
function createFullscreenCompose(compactInput, options = {}) {
  if (!compactInput) {
    console.warn('[FullscreenCompose] No compact input provided');
    return null;
  }

  // Create modal instance
  const modal = new FullscreenComposeModal({
    compactInput,
    ...options
  });

  // Simple swipe-up detection
  let startY = 0;
  let startTime = 0;
  let isTracking = false;
  const threshold = 120;
  const maxDuration = 500;

  const handleTouchStart = (e) => {
    if (e.touches.length === 1) {
      startY = e.touches[0].clientY;
      startTime = Date.now();
      isTracking = true;
    }
  };

  const handleTouchMove = (e) => {
    if (!isTracking) return;

    const currentY = e.touches[0].clientY;
    const deltaY = startY - currentY;

    // Check if swiping up beyond threshold
    if (deltaY > threshold) {
      const duration = Date.now() - startTime;
      if (duration < maxDuration) {
        isTracking = false;
        modal.open();
      }
    }
  };

  const handleTouchEnd = () => {
    isTracking = false;
  };

  compactInput.addEventListener('touchstart', handleTouchStart, { passive: true });
  compactInput.addEventListener('touchmove', handleTouchMove, { passive: true });
  compactInput.addEventListener('touchend', handleTouchEnd, { passive: true });

  // Return cleanup function
  const cleanup = () => {
    compactInput.removeEventListener('touchstart', handleTouchStart);
    compactInput.removeEventListener('touchmove', handleTouchMove);
    compactInput.removeEventListener('touchend', handleTouchEnd);
    modal.destroy();
  };

  return { modal, cleanup };
}

// Export for different module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    FullscreenComposeModal,
    createFullscreenCompose,
  };
}

if (typeof window !== 'undefined') {
  window.FullscreenCompose = {
    FullscreenComposeModal,
    createFullscreenCompose,
  };
}
