/**
 * Pull to Refresh - Visual Indicator Component
 *
 * Glassmorphism pull indicator with smooth animations.
 * Manages DOM element lifecycle and CSS custom properties.
 */

/**
 * PullIndicator - Visual feedback component for pull-to-refresh
 *
 * Creates and manages a glassmorphism indicator that shows pull progress
 * and state changes. Updates CSS custom properties for smooth animations.
 */
class PullIndicator {
  /**
   * Create a new PullIndicator instance
   *
   * @param {Object} options - Configuration options
   * @param {HTMLElement} options.container - Container element to append indicator to (default: document.body)
   * @param {Object} options.text - Text labels for different states
   * @param {string} options.text.pulling - Text shown while pulling (default: 'Pull to reconnect')
   * @param {string} options.text.ready - Text shown when ready to release (default: 'Release to reconnect')
   * @param {string} options.text.refreshing - Text shown while refreshing (default: 'Reconnecting...')
   * @param {string} options.id - ID for the indicator element (default: 'pull-indicator')
   */
  constructor(options = {}) {
    this.container = options.container || document.body;
    this.id = options.id || 'pull-indicator';

    // Text labels
    this.text = {
      pulling: options.text?.pulling || 'Pull to reconnect',
      ready: options.text?.ready || 'Release to reconnect',
      refreshing: options.text?.refreshing || 'Reconnecting...',
    };

    // DOM element reference
    this.element = null;

    // Current state
    this.state = 'hidden'; // 'hidden', 'pulling', 'ready', 'refreshing', 'success', 'error'
    this.progress = 0;

    // Create the DOM element
    this._createElement();
  }

  /**
   * Create the indicator DOM element
   * @private
   */
  _createElement() {
    // Remove existing element if present
    const existing = document.getElementById(this.id);
    if (existing) {
      existing.remove();
    }

    // Create container
    this.element = document.createElement('div');
    this.element.id = this.id;
    this.element.className = 'ptr-indicator ptr--hidden';
    this.element.setAttribute('role', 'status');
    this.element.setAttribute('aria-live', 'polite');
    this.element.setAttribute('aria-label', this.text.pulling);

    // Create spinner with arrow icon
    const spinner = document.createElement('div');
    spinner.className = 'ptr-spinner';
    spinner.innerHTML = `
      <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
        <path d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41z"/>
      </svg>
    `;

    // Create text label
    const text = document.createElement('span');
    text.className = 'ptr-text';
    text.textContent = this.text.pulling;

    // Assemble
    this.element.appendChild(spinner);
    this.element.appendChild(text);

    // Append to container
    this.container.appendChild(this.element);
  }

  /**
   * Show the indicator (called when pull starts)
   */
  show() {
    if (!this.element) return;

    this.state = 'pulling';
    this.element.classList.remove('ptr--hidden');
    this.element.classList.add('ptr--pulling');
    this.element.classList.remove('ptr--ready', 'ptr--refreshing', 'ptr--success', 'ptr--error');

    // Reset CSS custom properties
    this._updateCSSVariables(0, 0);

    // Update ARIA label
    this.element.setAttribute('aria-label', this.text.pulling);
  }

  /**
   * Hide the indicator (called when pull ends or cancels)
   * @param {number} delay - Optional delay before hiding (ms)
   */
  hide(delay = 0) {
    if (!this.element) return;

    const doHide = () => {
      this.state = 'hidden';
      this.progress = 0;
      this.element.classList.add('ptr--hidden');
      this.element.classList.remove('ptr--pulling', 'ptr--ready', 'ptr--refreshing');
      this._updateCSSVariables(0, 0);
    };

    if (delay > 0) {
      setTimeout(doHide, delay);
    } else {
      doHide();
    }
  }

  /**
   * Update the indicator based on pull progress
   *
   * @param {number} progress - Pull progress from 0 to 1
   * @param {number} distance - Pull distance in pixels
   */
  update(progress, distance = 0) {
    if (!this.element) return;

    // Clamp progress to 0-1 range
    this.progress = Math.max(0, Math.min(1, progress));

    // Update state based on progress
    const newState = this.progress >= 1 ? 'ready' : 'pulling';
    if (newState !== this.state && this.state !== 'refreshing') {
      this.setState(newState);
    }

    // Update CSS custom properties
    this._updateCSSVariables(this.progress, distance);
  }

  /**
   * Set the indicator state
   *
   * @param {string} state - One of: 'pulling', 'ready', 'refreshing', 'success', 'error', 'hidden'
   */
  setState(state) {
    if (!this.element) return;

    this.state = state;

    // Remove all state classes
    this.element.classList.remove(
      'ptr--pulling',
      'ptr--ready',
      'ptr--refreshing',
      'ptr--success',
      'ptr--error',
      'ptr--hidden'
    );

    // Add current state class
    this.element.classList.add(`ptr--${state}`);

    // Update ARIA label based on state
    const labels = {
      pulling: this.text.pulling,
      ready: this.text.ready,
      refreshing: this.text.refreshing,
      success: 'Connected!',
      error: 'Failed to connect',
    };

    if (labels[state]) {
      this.element.setAttribute('aria-label', labels[state]);
    }

    // Update text content for states that don't use CSS content
    const textEl = this.element.querySelector('.ptr-text');
    if (textEl && (state === 'success' || state === 'error')) {
      textEl.textContent = labels[state];
    }
  }

  /**
   * Show success state (connected)
   * @param {number} hideDelay - Delay before hiding (default: 1500ms)
   */
  showSuccess(hideDelay = 1500) {
    this.setState('success');
    if (hideDelay > 0) {
      this.hide(hideDelay);
    }
  }

  /**
   * Show error state (failed to connect)
   * @param {number} hideDelay - Delay before hiding (default: 2000ms)
   */
  showError(hideDelay = 2000) {
    this.setState('error');
    if (hideDelay > 0) {
      this.hide(hideDelay);
    }
  }

  /**
   * Update CSS custom properties for animations
   *
   * @param {number} progress - Pull progress (0-1)
   * @param {number} distance - Pull distance in pixels
   * @private
   */
  _updateCSSVariables(progress, distance) {
    if (!this.element) return;

    this.element.style.setProperty('--ptr-progress', String(progress));
    this.element.style.setProperty('--ptr-distance', `${distance}px`);
    this.element.style.setProperty('--ptr-opacity', String(progress));
    this.element.style.setProperty('--ptr-translate', `${(1 - progress) * -40}px`);
  }

  /**
   * Check if indicator is currently visible
   * @returns {boolean}
   */
  isVisible() {
    return this.state !== 'hidden' && this.element && !this.element.classList.contains('ptr--hidden');
  }

  /**
   * Get current state
   * @returns {string}
   */
  getState() {
    return this.state;
  }

  /**
   * Get current progress
   * @returns {number}
   */
  getProgress() {
    return this.progress;
  }

  /**
   * Destroy the indicator and clean up
   */
  destroy() {
    if (this.element && this.element.parentNode) {
      this.element.parentNode.removeChild(this.element);
    }
    this.element = null;
    this.state = 'hidden';
    this.progress = 0;
  }
}

/**
 * Factory function to create and wire up a PullIndicator with a PullToRefreshDetector
 *
 * @param {PullToRefreshDetector} detector - The detector instance to wire up
 * @param {Object} options - Options passed to PullIndicator constructor
 * @returns {PullIndicator} The created indicator instance
 */
function createPullIndicator(detector, options = {}) {
  const indicator = new PullIndicator(options);

  // Store original callbacks
  const originalCallbacks = {
    onPullStart: detector.onPullStart,
    onPullMove: detector.onPullMove,
    onPullEnd: detector.onPullEnd,
    onPullCancel: detector.onPullCancel,
    onRefresh: detector.onRefresh,
  };

  // Wire up indicator to detector callbacks
  detector.onPullStart = (detail) => {
    indicator.show();
    if (typeof originalCallbacks.onPullStart === 'function') {
      originalCallbacks.onPullStart(detail);
    }
  };

  detector.onPullMove = (detail) => {
    indicator.update(detail.progress, detail.displayDistance);
    if (typeof originalCallbacks.onPullMove === 'function') {
      originalCallbacks.onPullMove(detail);
    }
  };

  detector.onPullEnd = (detail) => {
    if (detail.refreshed) {
      indicator.setState('refreshing');
    } else {
      indicator.hide();
    }
    if (typeof originalCallbacks.onPullEnd === 'function') {
      originalCallbacks.onPullEnd(detail);
    }
  };

  detector.onPullCancel = (detail) => {
    indicator.hide();
    if (typeof originalCallbacks.onPullCancel === 'function') {
      originalCallbacks.onPullCancel(detail);
    }
  };

  detector.onRefresh = async (detail) => {
    indicator.setState('refreshing');

    try {
      // Call original callback and await if it's async
      if (typeof originalCallbacks.onRefresh === 'function') {
        await originalCallbacks.onRefresh(detail);
      }

      // Success - show connected state
      indicator.showSuccess(1500);

    } catch (error) {
      // Failure - show error state
      indicator.showError(2000);

      // Re-throw error for upstream handling
      throw error;
    }
  };

  // Store reference for cleanup
  indicator._detector = detector;
  indicator._originalCallbacks = originalCallbacks;

  return indicator;
}

// Export for different module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    PullIndicator,
    createPullIndicator,
  };
}

if (typeof window !== 'undefined') {
  window.PullIndicator = PullIndicator;
  window.createPullIndicator = createPullIndicator;
}
