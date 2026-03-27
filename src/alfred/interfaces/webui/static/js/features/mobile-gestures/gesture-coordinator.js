/**
 * GestureCoordinator - Central coordination for mobile gestures
 *
 * Manages gesture exclusivity, priority, and prevents conflicts between
 * multiple gesture detectors operating on the same page.
 *
 * Uses singleton pattern - one coordinator per page.
 */
class GestureCoordinator {
  /**
   * Private constructor - use getInstance() instead
   * @private
   */
  constructor() {
    if (GestureCoordinator.instance) {
      throw new Error('GestureCoordinator is a singleton - use getInstance()');
    }

    /** @type {Object|null} Currently active gesture info */
    this.activeGesture = null;
  }

  /**
   * Get the singleton instance
   * @returns {GestureCoordinator}
   */
  static getInstance() {
    if (!GestureCoordinator.instance) {
      GestureCoordinator.instance = new GestureCoordinator();
    }
    return GestureCoordinator.instance;
  }

  /**
   * Request a gesture lock
   *
   * @param {string} type - Gesture type identifier (e.g., 'swipe', 'longpress')
   * @param {number} priority - Priority level (higher = more important)
   * @param {Object} options - Additional options
   * @param {HTMLElement} options.element - Target element
   * @param {string} options.region - UI region identifier
   * @returns {boolean} True if lock granted, false if denied
   */
  requestGesture(type, priority = 1, options = {}) {
    // If no gesture is active, grant immediately
    if (!this.activeGesture) {
      this.activeGesture = {
        type,
        priority,
        startTime: Date.now(),
        element: options.element || null,
        region: options.region || 'default'
      };
      return true;
    }

    // If same gesture type, allow (renew the lock)
    if (this.activeGesture.type === type) {
      this.activeGesture.startTime = Date.now();
      this.activeGesture.element = options.element || null;
      this.activeGesture.region = options.region || 'default';
      return true;
    }

    // Higher priority can preempt lower priority
    if (priority > this.activeGesture.priority) {
      this.activeGesture = {
        type,
        priority,
        startTime: Date.now(),
        element: options.element || null,
        region: options.region || 'default'
      };
      return true;
    }

    // Equal or lower priority cannot preempt
    return false;
  }

  /**
   * Release the current gesture lock
   */
  releaseGesture() {
    this.activeGesture = null;
  }

  /**
   * Get information about the currently active gesture
   *
   * @returns {Object|null} Active gesture info or null if none
   */
  getActiveGesture() {
    return this.activeGesture ? { ...this.activeGesture } : null;
  }

  /**
   * Check if a specific gesture type (or any gesture) is active
   *
   * @param {string} [type] - Specific gesture type to check, or omit to check any
   * @returns {boolean}
   */
  isGestureActive(type) {
    if (!this.activeGesture) {
      return false;
    }

    if (type === undefined) {
      return true; // Any gesture is active
    }

    return this.activeGesture.type === type;
  }
}

// Static instance holder
GestureCoordinator.instance = null;

// Export for ESM and browser usage
export { GestureCoordinator };

if (typeof window !== 'undefined') {
  window.GestureCoordinator = {
    GestureCoordinator,
  };
}
