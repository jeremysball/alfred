/**
 * Toast Container Web Component
 *
 * Usage: <toast-container></toast-container>
 *
 * Toast levels: info, success, warning, error
 *
 * JavaScript API:
 *   const container = document.querySelector('toast-container');
 *   container.show(message, level, duration);
 *   container.show('Task completed', 'success', 3000);
 */
class ToastContainer extends HTMLElement {
  constructor() {
    super();
    this._toasts = [];
    this._toastIdCounter = 0;
  }

  connectedCallback() {
    this._render();
  }

  _render() {
    this.innerHTML = `
      <div class="toast-container">
        <!-- Toasts will be inserted here -->
      </div>
    `;
  }

  /**
   * Show a toast notification
   * @param {string} message - The message to display
   * @param {string} level - The toast level (info, success, warning, error)
   * @param {number} duration - Duration in milliseconds (default: 5000)
   * @returns {number} The toast ID
   */
  show(message, level = 'info', duration = 5000) {
    const id = ++this._toastIdCounter;
    const toast = {
      id,
      message,
      level,
      duration,
      element: null,
      timeoutId: null,
    };

    this._toasts.push(toast);
    this._renderToast(toast);

    // Auto-dismiss after duration
    if (duration > 0) {
      toast.timeoutId = setTimeout(() => {
        this.dismiss(id);
      }, duration);
    }

    return id;
  }

  /**
   * Dismiss a toast by ID
   * @param {number} id - The toast ID to dismiss
   */
  dismiss(id) {
    const index = this._toasts.findIndex(t => t.id === id);
    if (index === -1) return;

    const toast = this._toasts[index];

    // Clear timeout if exists
    if (toast.timeoutId) {
      clearTimeout(toast.timeoutId);
    }

    // Add exit animation
    if (toast.element) {
      toast.element.classList.add('toast-exit');

      // Remove after animation
      setTimeout(() => {
        toast.element?.remove();
        this._toasts.splice(index, 1);
      }, 300);
    } else {
      this._toasts.splice(index, 1);
    }
  }

  /**
   * Dismiss all toasts
   */
  dismissAll() {
    // Copy array since dismiss() modifies the original
    [...this._toasts].forEach(toast => this.dismiss(toast.id));
  }

  _renderToast(toast) {
    const container = this.querySelector('.toast-container');
    if (!container) return;

    const toastEl = document.createElement('div');
    toastEl.className = `toast toast-${toast.level}`;
    toastEl.setAttribute('data-toast-id', toast.id);

    // Icon based on level
    const icon = this._getIcon(toast.level);

    toastEl.innerHTML = `
      <span class="toast-icon">${icon}</span>
      <span class="toast-message">${this._escapeHtml(toast.message)}</span>
      <button class="toast-close" aria-label="Dismiss">&times;</button>
    `;

    // Close button handler
    const closeBtn = toastEl.querySelector('.toast-close');
    closeBtn.addEventListener('click', () => this.dismiss(toast.id));

    // Click to dismiss (optional - can be disabled)
    toastEl.addEventListener('click', (e) => {
      if (e.target !== closeBtn) {
        this.dismiss(toast.id);
      }
    });

    container.appendChild(toastEl);
    toast.element = toastEl;

    // Trigger enter animation
    requestAnimationFrame(() => {
      toastEl.classList.add('toast-enter');
    });
  }

  _getIcon(level) {
    const icons = {
      info: 'ℹ️',
      success: '✅',
      warning: '⚠️',
      error: '❌',
    };
    return icons[level] || icons.info;
  }

  _escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // Convenience methods for different levels
  info(message, duration) {
    return this.show(message, 'info', duration);
  }

  success(message, duration) {
    return this.show(message, 'success', duration);
  }

  warning(message, duration) {
    return this.show(message, 'warning', duration);
  }

  error(message, duration) {
    return this.show(message, 'error', duration);
  }
}

// Register the custom element
customElements.define('toast-container', ToastContainer);
