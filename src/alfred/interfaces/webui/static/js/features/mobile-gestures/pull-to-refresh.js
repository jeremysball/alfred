/**
 * Pull to Refresh helpers and detector
 *
 * Shared utilities for mobile pull-to-refresh behavior.
 */

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

/**
 * Check whether a scroll container is at the top, with an optional tolerance.
 *
 * @param {Object} element - Scroll container with a scrollTop property.
 * @param {number} threshold - Allowable top-offset tolerance in pixels.
 * @returns {boolean} True when the container is at or near the top.
 */
function isScrolledToTop(element, threshold = 10) {
  if (!element || typeof element.scrollTop !== 'number') {
    return false;
  }

  const scrollTop = Math.max(0, element.scrollTop);
  const tolerance = Number.isFinite(threshold) ? Math.max(0, threshold) : 0;

  return scrollTop <= tolerance;
}

/**
 * Pull-to-refresh detector.
 *
 * Tracks a vertical drag from the top of a scroll container and fires a
 * refresh callback when the pull exceeds the configured threshold.
 */
class PullToRefreshDetector {
  constructor(options = {}) {
    this.threshold = Number.isFinite(options.threshold) ? Math.max(1, options.threshold) : 80;
    this.topThreshold = Number.isFinite(options.topThreshold) ? Math.max(0, options.topThreshold) : 10;
    this.resistance = Number.isFinite(options.resistance)
      ? clamp(options.resistance, 0.1, 1)
      : 0.5;

    this.enableVisualFeedback = options.enableVisualFeedback !== false;
    this.onRefresh = typeof options.onRefresh === 'function' ? options.onRefresh : () => {};
    this.onPullStart = typeof options.onPullStart === 'function' ? options.onPullStart : null;
    this.onPullMove = typeof options.onPullMove === 'function' ? options.onPullMove : null;
    this.onPullEnd = typeof options.onPullEnd === 'function' ? options.onPullEnd : null;
    this.onPullCancel = typeof options.onPullCancel === 'function' ? options.onPullCancel : null;

    this._element = null;
    this._scrollContainer = null;
    this._isTracking = false;
    this._isPulling = false;
    this._startX = 0;
    this._startY = 0;
    this._currentX = 0;
    this._currentY = 0;
    this._startScrollTop = 0;
    this._lastRawDistance = 0;
    this._lastDisplayDistance = 0;
    this._lastProgress = 0;

    this._handleTouchStart = this._handleTouchStart.bind(this);
    this._handleTouchMove = this._handleTouchMove.bind(this);
    this._handleTouchEnd = this._handleTouchEnd.bind(this);
  }

  /**
   * Attach detector to a scrollable element.
   *
   * @param {HTMLElement} element - Element that receives touch events.
   * @param {HTMLElement} [scrollContainer] - Scroll container to inspect.
   * @returns {boolean}
   */
  attachToElement(element, scrollContainer = null) {
    if (!element || !(element instanceof HTMLElement)) {
      console.error('PullToRefreshDetector: Invalid element provided');
      return false;
    }

    this.detach();

    this._element = element;
    this._scrollContainer = scrollContainer || element;

    element.addEventListener('touchstart', this._handleTouchStart, { passive: true });
    element.addEventListener('touchmove', this._handleTouchMove, { passive: false });
    element.addEventListener('touchend', this._handleTouchEnd, { passive: true });
    element.addEventListener('touchcancel', this._handleTouchEnd, { passive: true });

    return true;
  }

  /**
   * Detach event listeners and clear state.
   */
  detach() {
    if (this._element) {
      this._element.removeEventListener('touchstart', this._handleTouchStart);
      this._element.removeEventListener('touchmove', this._handleTouchMove);
      this._element.removeEventListener('touchend', this._handleTouchEnd);
      this._element.removeEventListener('touchcancel', this._handleTouchEnd);
    }

    this._resetTrackingState();
    this._element = null;
    this._scrollContainer = null;
  }

  /**
   * Destroy detector and release callbacks.
   */
  destroy() {
    this.detach();
    this.onRefresh = null;
    this.onPullStart = null;
    this.onPullMove = null;
    this.onPullEnd = null;
    this.onPullCancel = null;
  }

  /**
   * Handle touch start.
   * @param {TouchEvent} event
   */
  _handleTouchStart(event) {
    if (!event || !event.touches || event.touches.length === 0) {
      return;
    }

    if (!this._isAtTop()) {
      this._resetTrackingState();
      return;
    }

    const touch = event.touches[0];
    this._isTracking = true;
    this._isPulling = false;
    this._startX = touch.clientX;
    this._startY = touch.clientY;
    this._currentX = touch.clientX;
    this._currentY = touch.clientY;
    this._startScrollTop = this._getScrollTop();
    this._lastRawDistance = 0;
    this._lastDisplayDistance = 0;
    this._lastProgress = 0;

    if (this.onPullStart) {
      this.onPullStart(this._getDetail({ event }));
    }
  }

  /**
   * Handle touch move.
   * @param {TouchEvent} event
   */
  _handleTouchMove(event) {
    if (!this._isTracking || !event || !event.touches || event.touches.length === 0) {
      return;
    }

    if (!this._isAtTop()) {
      this._cancelTracking('left-top-zone', event);
      return;
    }

    const touch = event.touches[0];
    this._currentX = touch.clientX;
    this._currentY = touch.clientY;

    const rawDistance = this._currentY - this._startY;

    if (rawDistance <= 0) {
      this._cancelTracking('moved-upward', event);
      return;
    }

    this._isPulling = true;
    this._lastRawDistance = rawDistance;
    this._lastDisplayDistance = this._calculateDisplayDistance(rawDistance);
    this._lastProgress = Math.min(rawDistance / this.threshold, 1);

    if (this.enableVisualFeedback) {
      this._applyVisualFeedback(this._lastDisplayDistance, this._lastProgress);
    }

    if (typeof event.preventDefault === 'function') {
      event.preventDefault();
    }

    if (this.onPullMove) {
      this.onPullMove(this._getDetail({ event }));
    }
  }

  /**
   * Handle touch end or cancel.
   * @param {TouchEvent} event
   */
  _handleTouchEnd(event) {
    if (!this._isTracking) {
      return;
    }

    const detail = this._getDetail({ event });
    const shouldRefresh = this._lastRawDistance >= this.threshold;

    if (shouldRefresh) {
      this.onRefresh(detail);
    } else if (this.onPullCancel) {
      this.onPullCancel(detail);
    }

    if (this.onPullEnd) {
      this.onPullEnd({
        ...detail,
        refreshed: shouldRefresh,
      });
    }

    this._snapBack();
    this._resetTrackingState();
  }

  /**
   * Calculate the displayed pull distance with resistance.
   *
   * @param {number} rawDistance
   * @returns {number}
   */
  _calculateDisplayDistance(rawDistance) {
    const distance = Math.max(0, rawDistance);

    if (distance === 0) {
      return 0;
    }

    if (distance <= this.threshold) {
      return distance * this.resistance;
    }

    const extra = distance - this.threshold;
    return (this.threshold * this.resistance) + (extra * this.resistance * 0.35);
  }

  /**
   * Apply visual feedback during the pull.
   *
   * @param {number} displayDistance
   * @param {number} progress
   */
  _applyVisualFeedback(displayDistance, progress) {
    if (!this._element) {
      return;
    }

    this._element.classList.add('pull-to-refresh--pulling');
    this._element.style.transform = `translateY(${displayDistance}px)`;
    this._element.style.transition = 'none';
    this._element.style.opacity = String(1 - (progress * 0.12));
    this._element.style.willChange = 'transform, opacity';
    this._element.dataset.pullState = progress >= 1 ? 'ready' : 'pulling';
    this._element.dataset.pullProgress = String(progress);
  }

  /**
   * Snap the element back after release.
   */
  _snapBack() {
    if (!this._element) {
      return;
    }

    this._element.classList.remove('pull-to-refresh--pulling');
    this._element.style.transition = 'transform 300ms cubic-bezier(0.4, 0.0, 0.2, 1), opacity 300ms ease';
    this._element.style.transform = 'translateY(0)';
    this._element.style.opacity = '1';
    this._element.style.willChange = '';
    delete this._element.dataset.pullState;
    delete this._element.dataset.pullProgress;
  }

  /**
   * Cancel an in-progress pull.
   *
   * @param {string} reason
   * @param {TouchEvent} event
   */
  _cancelTracking(reason, event) {
    if (!this._isTracking) {
      return;
    }

    const detail = this._getDetail({ event, reason });

    if (this.onPullCancel) {
      this.onPullCancel(detail);
    }

    this._snapBack();
    this._resetTrackingState();
  }

  /**
   * Build a consistent detail payload.
   *
   * @param {Object} extras
   * @returns {Object}
   */
  _getDetail(extras = {}) {
    return {
      element: this._element,
      scrollContainer: this._scrollContainer,
      startX: this._startX,
      startY: this._startY,
      currentX: this._currentX,
      currentY: this._currentY,
      startScrollTop: this._startScrollTop,
      rawDistance: this._lastRawDistance,
      displayDistance: this._lastDisplayDistance,
      progress: this._lastProgress,
      isPulling: this._isPulling,
      ...extras,
    };
  }

  /**
   * Check whether the current scroll container is at the top.
   *
   * @returns {boolean}
   */
  _isAtTop() {
    return isScrolledToTop(this._scrollContainer, this.topThreshold);
  }

  /**
   * Read current scrollTop safely.
   *
   * @returns {number}
   */
  _getScrollTop() {
    if (!this._scrollContainer || typeof this._scrollContainer.scrollTop !== 'number') {
      return 0;
    }

    return Math.max(0, this._scrollContainer.scrollTop);
  }

  /**
   * Reset transient tracking state.
   */
  _resetTrackingState() {
    this._isTracking = false;
    this._isPulling = false;
    this._startX = 0;
    this._startY = 0;
    this._currentX = 0;
    this._currentY = 0;
    this._startScrollTop = 0;
    this._lastRawDistance = 0;
    this._lastDisplayDistance = 0;
    this._lastProgress = 0;
  }
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    isScrolledToTop,
    PullToRefreshDetector,
  };
}

if (typeof window !== 'undefined') {
  window.PullToRefresh = {
    isScrolledToTop,
    PullToRefreshDetector,
  };
}
