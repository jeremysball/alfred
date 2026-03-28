/**
 * Swipe Detector
 *
 * Detects swipe gestures on touch devices.
 * Supports horizontal and vertical swipe detection with configurable threshold.
 *
 * Usage:
 *   const detector = new SwipeDetector({
 *     threshold: 100,
 *     direction: 'horizontal',
 *     edgeMargin: 40,
 *     onSwipe: (direction, distance, event) => handleSwipe(direction, distance)
 *   });
 *   detector.attachToElement(element);
 */

class SwipeDetector {
  constructor(options = {}) {
    this.threshold = options.threshold || 100;
    this.direction = options.direction || "horizontal"; // 'horizontal', 'vertical', or 'both'
    this.edgeMargin = options.edgeMargin !== undefined ? options.edgeMargin : 40;
    this.excludeSelectors = options.excludeSelectors || [
      "input",
      "textarea",
      "select",
      "[contenteditable]",
    ];

    // Callbacks
    this.onSwipe = options.onSwipe || null;
    this.onSwipeStart = options.onSwipeStart || null;
    this.onSwipeMove = options.onSwipeMove || null;
    this.onSwipeEnd = options.onSwipeEnd || null;

    // State
    this._element = null;
    this._isActive = false;
    this._startX = 0;
    this._startY = 0;
    this._currentX = 0;
    this._currentY = 0;
    this._startTime = 0;
    this._screenWidth = 0;

    // Bound handlers
    this._handleTouchStart = this._handleTouchStart.bind(this);
    this._handleTouchMove = this._handleTouchMove.bind(this);
    this._handleTouchEnd = this._handleTouchEnd.bind(this);
  }

  /**
   * Attach swipe detection to a DOM element
   * @param {HTMLElement} element - The element to attach to
   */
  attachToElement(element) {
    if (!element || !(element instanceof HTMLElement)) {
      console.error("SwipeDetector: Invalid element provided");
      return false;
    }

    this.detach();

    this._element = element;
    this._screenWidth = window.innerWidth;

    // Use passive listeners for better scroll performance
    element.addEventListener("touchstart", this._handleTouchStart, { passive: true });
    element.addEventListener("touchmove", this._handleTouchMove, { passive: true });
    element.addEventListener("touchend", this._handleTouchEnd, { passive: true });
    element.addEventListener("touchcancel", this._handleTouchEnd, { passive: true });

    // Update screen width on resize
    window.addEventListener("resize", this._updateScreenWidth.bind(this));

    return true;
  }

  /**
   * Detach all event listeners
   */
  detach() {
    if (!this._element) return;

    this._element.removeEventListener("touchstart", this._handleTouchStart);
    this._element.removeEventListener("touchmove", this._handleTouchMove);
    this._element.removeEventListener("touchend", this._handleTouchEnd);
    this._element.removeEventListener("touchcancel", this._handleTouchEnd);

    this._element = null;
    this._isActive = false;
  }

  /**
   * Update screen width reference
   */
  _updateScreenWidth() {
    this._screenWidth = window.innerWidth;
  }

  /**
   * Check if we should handle this touch (not in edge zone, not on excluded element)
   * @param {number} touchX - Starting X position
   * @param {number} screenWidth - Screen width
   * @param {HTMLElement} target - Touch target element
   * @returns {boolean}
   */
  _shouldHandleTouch(touchX, screenWidth, target) {
    // Check edge zone
    if (this.edgeMargin > 0) {
      const isLeftEdge = touchX < this.edgeMargin;
      const isRightEdge = touchX > screenWidth - this.edgeMargin;
      if (isLeftEdge || isRightEdge) {
        return false;
      }
    }

    // Check excluded elements
    if (target && this.excludeSelectors.length > 0) {
      for (const selector of this.excludeSelectors) {
        if (target.matches(selector) || target.closest(selector)) {
          return false;
        }
      }
    }

    return true;
  }

  /**
   * Handle touch start
   * @param {TouchEvent} event
   */
  _handleTouchStart(event) {
    const touch = event.touches[0];
    this._startX = touch.clientX;
    this._startY = touch.clientY;
    this._currentX = touch.clientX;
    this._currentY = touch.clientY;
    this._startTime = Date.now();

    // Check if we should handle this touch
    if (!this._shouldHandleTouch(this._startX, this._screenWidth, event.target)) {
      this._isActive = false;
      return;
    }

    this._isActive = true;

    if (typeof this.onSwipeStart === "function") {
      this.onSwipeStart(event);
    }
  }

  /**
   * Handle touch move
   * @param {TouchEvent} event
   */
  _handleTouchMove(event) {
    if (!this._isActive) return;

    const touch = event.touches[0];
    this._currentX = touch.clientX;
    this._currentY = touch.clientY;

    const deltaX = this._currentX - this._startX;
    const deltaY = this._currentY - this._startY;

    if (typeof this.onSwipeMove === "function") {
      this.onSwipeMove(deltaX, deltaY, event);
    }
  }

  /**
   * Handle touch end
   * @param {TouchEvent} event
   */
  _handleTouchEnd(event) {
    if (!this._isActive) return;

    const result = this._calculateSwipe(this._currentX, this._currentY);

    if (typeof this.onSwipeEnd === "function") {
      this.onSwipeEnd(result, event);
    }

    if (result.isValid && typeof this.onSwipe === "function") {
      this.onSwipe(result.direction, result.distance, event, result);
    }

    this._isActive = false;
  }

  /**
   * Calculate swipe result from current position
   * @param {number} currentX - Current X position
   * @param {number} currentY - Current Y position
   * @returns {Object} Swipe result with direction, distance, and validity
   */
  _calculateSwipe(currentX, currentY) {
    const deltaX = currentX - this._startX;
    const deltaY = currentY - this._startY;

    const absX = Math.abs(deltaX);
    const absY = Math.abs(deltaY);

    const isHorizontal = absX > absY;
    const isVertical = absY >= absX;

    let direction = null;
    let distance = 0;
    let isValid = false;

    if (isHorizontal) {
      distance = absX;
      direction = deltaX > 0 ? "right" : "left";

      if (this.direction === "horizontal" || this.direction === "both") {
        isValid = distance >= this.threshold;
      }
    } else {
      distance = absY;
      direction = deltaY > 0 ? "down" : "up";

      if (this.direction === "vertical" || this.direction === "both") {
        isValid = distance >= this.threshold;
      }
    }

    return {
      direction,
      distance,
      isValid,
      isHorizontal,
      isVertical,
      deltaX,
      deltaY,
      duration: Date.now() - this._startTime,
    };
  }

  /**
   * Get current swipe progress (0-1) for visual feedback
   * @returns {number} Progress ratio
   */
  getProgress() {
    if (!this._isActive) return 0;

    const deltaX = this._currentX - this._startX;
    const deltaY = this._currentY - this._startY;
    const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY);

    return Math.min(distance / this.threshold, 1);
  }

  /**
   * Destroy the detector and clean up
   */
  destroy() {
    this.detach();
    this.onSwipe = null;
    this.onSwipeStart = null;
    this.onSwipeMove = null;
    this.onSwipeEnd = null;
  }
}

// Export for ESM and browser usage
export { SwipeDetector };

if (typeof window !== "undefined") {
  window.SwipeDetector = SwipeDetector;
}
