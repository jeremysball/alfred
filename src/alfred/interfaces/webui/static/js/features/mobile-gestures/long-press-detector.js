/**
 * Long Press Detector
 *
 * Detects long press gestures on touch devices.
 * Distinguishes from swipe gestures using movement tolerance.
 * Provides visual feedback during press with haptic support.
 *
 * Usage:
 *   const detector = new LongPressDetector({
 *     threshold: 500,
 *     movementTolerance: 10,
 *     onLongPress: (element) => showContextMenu(element),
 *     onPressStart: (element) => console.log('Press started'),
 *     onPressCancel: (element) => console.log('Press cancelled')
 *   });
 *   detector.attachToElement(element);
 *
 * Phase 3: Touch Gesture Support - Long Press Context Menu
 */

class LongPressDetector {
  constructor(options = {}) {
    // Configuration
    this.threshold = options.threshold || 500; // ms to trigger long press
    this.movementTolerance = options.movementTolerance || 10; // px movement allowed

    // Callbacks
    this.onLongPress = options.onLongPress || (() => {});
    this.onPressStart = options.onPressStart || (() => {});
    this.onPressCancel = options.onPressCancel || (() => {});

    // Feature flags
    this.enableHaptic = options.enableHaptic !== false; // Default true
    this.enableVisualFeedback = options.enableVisualFeedback !== false; // Default true

    // Visual feedback timing
    this.VISUAL_FEEDBACK_DELAY = 200; // ms before showing visual feedback
    this.VISUAL_SCALE = 0.98; // Scale factor during press
    this.VISUAL_OPACITY = 0.95; // Opacity during press

    // State
    this._element = null;
    this._isPressing = false;
    this._startX = 0;
    this._startY = 0;
    this._startTime = 0;
    this._visualFeedbackTimer = null;
    this._longPressTimer = null;

    // Bound handlers
    this._handleTouchStart = this._handleTouchStart.bind(this);
    this._handleTouchMove = this._handleTouchMove.bind(this);
    this._handleTouchEnd = this._handleTouchEnd.bind(this);
    this._handleTouchCancel = this._handleTouchCancel.bind(this);
  }

  /**
   * Attach long press detection to a DOM element
   * @param {HTMLElement} element - The element to attach to
   * @returns {boolean} Success status
   */
  attachToElement(element) {
    if (!element || !(element instanceof HTMLElement)) {
      console.error('LongPressDetector: Invalid element provided');
      return false;
    }

    this.detach();

    this._element = element;

    // Use passive listeners for better scroll performance
    element.addEventListener('touchstart', this._handleTouchStart, { passive: true });
    element.addEventListener('touchmove', this._handleTouchMove, { passive: true });
    element.addEventListener('touchend', this._handleTouchEnd, { passive: true });
    element.addEventListener('touchcancel', this._handleTouchCancel, { passive: true });

    return true;
  }

  /**
   * Detach all event listeners
   */
  detach() {
    if (!this._element) return;

    this._element.removeEventListener('touchstart', this._handleTouchStart);
    this._element.removeEventListener('touchmove', this._handleTouchMove);
    this._element.removeEventListener('touchend', this._handleTouchEnd);
    this._element.removeEventListener('touchcancel', this._handleTouchCancel);

    this._cancelPress();
    this._element = null;
  }

  /**
   * Handle touch start
   * @param {TouchEvent} event
   */
  _handleTouchStart(event) {
    const touch = event.touches[0];
    this._startX = touch.clientX;
    this._startY = touch.clientY;
    this._startTime = Date.now();
    this._isPressing = true;

    // Call press start callback
    this.onPressStart(this._element);

    // Schedule visual feedback
    this._visualFeedbackTimer = setTimeout(() => {
      if (this._isPressing && this.enableVisualFeedback) {
        this._applyVisualFeedback(this._element);
        if (this.enableHaptic) {
          this._triggerHaptic();
        }
      }
    }, this.VISUAL_FEEDBACK_DELAY);

    // Schedule long press detection
    this._longPressTimer = setTimeout(() => {
      if (this._isPressing) {
        this._isPressing = false; // Prevent duplicate triggers
        this._triggerLongPress();
      }
    }, this.threshold);
  }

  /**
   * Handle touch move
   * @param {TouchEvent} event
   */
  _handleTouchMove(event) {
    if (!this._isPressing) return;

    const touch = event.touches[0];
    const movement = this._calculateMovement(touch.clientX, touch.clientY);

    // Cancel if moved too far
    if (movement > this.movementTolerance) {
      this._cancelPress();
      this.onPressCancel(this._element);
    }
  }

  /**
   * Handle touch end
   * @param {TouchEvent} event
   */
  _handleTouchEnd(event) {
    if (!this._isPressing) return;

    const duration = Date.now() - this._startTime;

    // Check if threshold was met
    if (duration >= this.threshold) {
      this._triggerLongPress();
    } else {
      this.onPressCancel(this._element);
    }

    this._cancelPress();
  }

  /**
   * Handle touch cancel (e.g., interrupted by system)
   * @param {TouchEvent} event
   */
  _handleTouchCancel(event) {
    if (!this._isPressing) return;

    this._cancelPress();
    this.onPressCancel(this._element);
  }

  /**
   * Calculate movement distance from start position
   * @param {number} currentX - Current X position
   * @param {number} currentY - Current Y position
   * @returns {number} Euclidean distance
   */
  _calculateMovement(currentX, currentY) {
    const deltaX = currentX - this._startX;
    const deltaY = currentY - this._startY;
    return Math.sqrt(deltaX * deltaX + deltaY * deltaY);
  }

  /**
   * Apply visual feedback during press
   * @param {HTMLElement} element - The element being pressed
   */
  _applyVisualFeedback(element) {
    if (!element) return;

    element.style.transition = 'transform 0.15s ease, opacity 0.15s ease';
    element.style.transform = `scale(${this.VISUAL_SCALE})`;
    element.style.opacity = String(this.VISUAL_OPACITY);
  }

  /**
   * Reset visual state
   * @param {HTMLElement} element - The element to reset
   */
  _resetVisualState(element) {
    if (!element) return;

    element.style.transform = '';
    element.style.transition = '';
    element.style.opacity = '';
  }

  /**
   * Cancel the current press and clean up timers
   */
  _cancelPress() {
    this._isPressing = false;

    if (this._visualFeedbackTimer) {
      clearTimeout(this._visualFeedbackTimer);
      this._visualFeedbackTimer = null;
    }

    if (this._longPressTimer) {
      clearTimeout(this._longPressTimer);
      this._longPressTimer = null;
    }

    if (this._element) {
      this._resetVisualState(this._element);
    }
  }

  /**
   * Trigger haptic feedback
   */
  _triggerHaptic() {
    if (!this.enableHaptic) return;

    if (navigator.vibrate) {
      // Light tap to indicate visual feedback is starting
      navigator.vibrate(5);
    }
  }

  /**
   * Trigger long press callback
   */
  _triggerLongPress() {
    // Stronger haptic for confirmation
    if (this.enableHaptic && navigator.vibrate) {
      navigator.vibrate([10, 20, 10]);
    }

    this.onLongPress(this._element);
  }

  /**
   * Destroy the detector and clean up
   */
  destroy() {
    this._cancelPress();
    this.detach();

    // Clear callbacks
    this.onLongPress = null;
    this.onPressStart = null;
    this.onPressCancel = null;
  }
}

// Export for ESM and browser usage
export { LongPressDetector };

if (typeof window !== 'undefined') {
  window.LongPressDetector = LongPressDetector;
}
