/**
 * Coordinated Detector Wrappers
 *
 * Wraps SwipeDetector and LongPressDetector with GestureCoordinator integration.
 * Ensures gestures coordinate and don't conflict with each other.
 */

const { GestureCoordinator } = require('./gesture-coordinator.js');
const { SwipeDetector } = require('./swipe-detector.js');
const { LongPressDetector } = require('./long-press-detector.js');

/**
 * CoordinatedSwipeDetector - Wraps SwipeDetector with gesture coordination
 *
 * Requests a gesture lock from the coordinator before starting swipe detection.
 * Priority: 1 (standard)
 */
class CoordinatedSwipeDetector {
  /**
   * Create a coordinated swipe detector
   * @param {HTMLElement} element - Element to attach to
   * @param {Object} options - Configuration options
   * @param {Function} options.onSwipe - Callback when swipe completes
   * @param {number} options.threshold - Swipe threshold in pixels
   * @param {string} options.direction - Swipe direction ('left', 'right', 'both')
   */
  constructor(element, options = {}) {
    this.element = element;
    this.options = options;
    this.coordinator = GestureCoordinator.getInstance();
    this.isActive = false;

    // Axis locking properties
    this.axisLock = null; // 'horizontal', 'vertical', or null
    this.startX = 0;
    this.startY = 0;
    this.AXIS_THRESHOLD = 15;
    this.AXIS_DOMINANCE_RATIO = 1.5;

    // Create the wrapped detector (don't attach yet)
    this.wrappedDetector = new SwipeDetector({
      threshold: options.threshold || 100,
      direction: options.direction || 'both',
      onSwipe: (detail) => {
        // Only call callback if we have the lock
        if (this.isActive && typeof options.onSwipe === 'function') {
          options.onSwipe(detail);
        }
      }
    });

    // Bind methods
    this._handleTouchStart = this._handleTouchStart.bind(this);
    this._handleTouchMove = this._handleTouchMove.bind(this);
    this._handleTouchEnd = this._handleTouchEnd.bind(this);
    this._handleTouchCancel = this._handleTouchCancel.bind(this);
  }

  /**
   * Attach the detector to the element
   */
  attach() {
    if (!this.element) return;

    // Add our coordination listeners
    this.element.addEventListener('touchstart', this._handleTouchStart, { passive: true });
    this.element.addEventListener('touchmove', this._handleTouchMove, { passive: true });
    this.element.addEventListener('touchend', this._handleTouchEnd, { passive: true });
    this.element.addEventListener('touchcancel', this._handleTouchCancel, { passive: true });

    // Attach the wrapped detector
    this.wrappedDetector.attachToElement(this.element);
  }

  /**
   * Destroy the detector and clean up
   */
  destroy() {
    this._releaseLock();

    if (this.element) {
      this.element.removeEventListener('touchstart', this._handleTouchStart);
      this.element.removeEventListener('touchmove', this._handleTouchMove);
      this.element.removeEventListener('touchend', this._handleTouchEnd);
      this.element.removeEventListener('touchcancel', this._handleTouchCancel);
    }

    if (this.wrappedDetector) {
      this.wrappedDetector.destroy();
    }
  }

  /**
   * Handle touchstart - request gesture lock and store start position
   * @private
   */
  _handleTouchStart(e) {
    // Request lock with priority 1 (standard swipe)
    const granted = this.coordinator.requestGesture('swipe', 1, {
      element: this.element
    });

    if (granted) {
      this.isActive = true;
      // Store start position for axis locking
      if (e.touches && e.touches[0]) {
        this.startX = e.touches[0].clientX;
        this.startY = e.touches[0].clientY;
      }
    }
  }

  /**
   * Handle touchmove - check axis locking
   * @private
   */
  _handleTouchMove(e) {
    if (!this.isActive || !e.touches || !e.touches[0]) return;

    // If already locked, don't re-evaluate
    if (this.axisLock) return;

    const currentX = e.touches[0].clientX;
    const currentY = e.touches[0].clientY;

    const deltaX = Math.abs(currentX - this.startX);
    const deltaY = Math.abs(currentY - this.startY);

    // Check for horizontal lock
    if (deltaX > this.AXIS_THRESHOLD && 
        deltaX > deltaY * this.AXIS_DOMINANCE_RATIO) {
      this.axisLock = 'horizontal';
    }
    // Check for vertical lock
    else if (deltaY > this.AXIS_THRESHOLD && 
             deltaY > deltaX * this.AXIS_DOMINANCE_RATIO) {
      this.axisLock = 'vertical';
    }
    // Otherwise stay neutral (null)
  }

  /**
   * Handle touchend - release gesture lock
   * @private
   */
  _handleTouchEnd(e) {
    this._releaseLock();
  }

  /**
   * Handle touchcancel - release gesture lock
   * @private
   */
  _handleTouchCancel(e) {
    this._releaseLock();
  }

  /**
   * Release the gesture lock if we have it
   * @private
   */
  _releaseLock() {
    if (this.isActive) {
      this.coordinator.releaseGesture();
      this.isActive = false;
      this.axisLock = null;
      this.startX = 0;
      this.startY = 0;
    }
  }
}

/**
 * CoordinatedLongPressDetector - Wraps LongPressDetector with gesture coordination
 *
 * Requests a gesture lock from the coordinator before starting long press detection.
 * Priority: 3 (highest - intentional action)
 */
class CoordinatedLongPressDetector {
  /**
   * Create a coordinated long press detector
   * @param {HTMLElement} element - Element to attach to
   * @param {Object} options - Configuration options
   * @param {Function} options.onLongPress - Callback when long press completes
   * @param {number} options.delay - Long press delay in milliseconds
   * @param {number} options.tolerance - Movement tolerance in pixels
   */
  constructor(element, options = {}) {
    this.element = element;
    this.options = options;
    this.coordinator = GestureCoordinator.getInstance();
    this.isActive = false;

    // Axis locking properties (less critical for long press but included for consistency)
    this.axisLock = null;
    this.startX = 0;
    this.startY = 0;
    this.AXIS_THRESHOLD = 15;
    this.AXIS_DOMINANCE_RATIO = 1.5;

    // Create the wrapped detector (don't attach yet)
    this.wrappedDetector = new LongPressDetector({
      delay: options.delay || 500,
      tolerance: options.tolerance || 10,
      onLongPress: (detail) => {
        // Only call callback if we have the lock
        if (this.isActive && typeof options.onLongPress === 'function') {
          options.onLongPress(detail);
        }
      }
    });

    // Bind methods
    this._handleTouchStart = this._handleTouchStart.bind(this);
    this._handleTouchMove = this._handleTouchMove.bind(this);
    this._handleTouchEnd = this._handleTouchEnd.bind(this);
    this._handleTouchCancel = this._handleTouchCancel.bind(this);
  }

  /**
   * Attach the detector to the element
   */
  attach() {
    if (!this.element) return;

    // Add our coordination listeners
    this.element.addEventListener('touchstart', this._handleTouchStart, { passive: true });
    this.element.addEventListener('touchmove', this._handleTouchMove, { passive: true });
    this.element.addEventListener('touchend', this._handleTouchEnd, { passive: true });
    this.element.addEventListener('touchcancel', this._handleTouchCancel, { passive: true });

    // Attach the wrapped detector
    this.wrappedDetector.attachToElement(this.element);
  }

  /**
   * Destroy the detector and clean up
   */
  destroy() {
    this._releaseLock();

    if (this.element) {
      this.element.removeEventListener('touchstart', this._handleTouchStart);
      this.element.removeEventListener('touchmove', this._handleTouchMove);
      this.element.removeEventListener('touchend', this._handleTouchEnd);
      this.element.removeEventListener('touchcancel', this._handleTouchCancel);
    }

    if (this.wrappedDetector) {
      this.wrappedDetector.destroy();
    }
  }

  /**
   * Handle touchstart - request gesture lock
   * @private
   */
  _handleTouchStart(e) {
    // Request lock with priority 3 (highest - intentional long press)
    const granted = this.coordinator.requestGesture('longpress', 3, {
      element: this.element
    });

    if (granted) {
      this.isActive = true;
      // Store start position for axis locking
      if (e.touches && e.touches[0]) {
        this.startX = e.touches[0].clientX;
        this.startY = e.touches[0].clientY;
      }
    }
  }

  /**
   * Handle touchmove - check axis locking
   * @private
   */
  _handleTouchMove(e) {
    if (!this.isActive || !e.touches || !e.touches[0]) return;

    // If already locked, don't re-evaluate
    if (this.axisLock) return;

    const currentX = e.touches[0].clientX;
    const currentY = e.touches[0].clientY;

    const deltaX = Math.abs(currentX - this.startX);
    const deltaY = Math.abs(currentY - this.startY);

    // Check for horizontal lock
    if (deltaX > this.AXIS_THRESHOLD && 
        deltaX > deltaY * this.AXIS_DOMINANCE_RATIO) {
      this.axisLock = 'horizontal';
    }
    // Check for vertical lock
    else if (deltaY > this.AXIS_THRESHOLD && 
             deltaY > deltaX * this.AXIS_DOMINANCE_RATIO) {
      this.axisLock = 'vertical';
    }
    // Otherwise stay neutral (null)
  }

  /**
   * Handle touchend - release gesture lock
   * @private
   */
  _handleTouchEnd(e) {
    this._releaseLock();
  }

  /**
   * Handle touchcancel - release gesture lock
   * @private
   */
  _handleTouchCancel(e) {
    this._releaseLock();
  }

  /**
   * Release the gesture lock if we have it
   * @private
   */
  _releaseLock() {
    if (this.isActive) {
      this.coordinator.releaseGesture();
      this.isActive = false;
      this.axisLock = null;
      this.startX = 0;
      this.startY = 0;
    }
  }
}

// Export for different module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    CoordinatedSwipeDetector,
    CoordinatedLongPressDetector,
  };
}

if (typeof window !== 'undefined') {
  window.CoordinatedDetectors = {
    CoordinatedSwipeDetector,
    CoordinatedLongPressDetector,
  };
}
