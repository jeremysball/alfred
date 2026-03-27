/**
 * Toast Notification System
 *
 * In-app toast notifications for when browser notifications are denied.
 * Shows at the bottom of the screen with auto-dismiss.
 */

let toastContainer = null;
let toastId = 0;
const activeToasts = new Map();

/**
 * Create toast container
 * @private
 */
function createContainer() {
  if (toastContainer) return;

  toastContainer = document.createElement('div');
  toastContainer.className = 'toast-container';
  toastContainer.setAttribute('role', 'status');
  toastContainer.setAttribute('aria-live', 'polite');
  toastContainer.setAttribute('aria-atomic', 'true');

  document.body.appendChild(toastContainer);
}

/**
 * Show a toast notification
 * @param {Object} options
 * @param {string} options.message - Toast message
 * @param {string} [options.type='info'] - 'info', 'success', 'warning', 'error'
 * @param {number} [options.duration=5000] - Duration in milliseconds
 * @param {boolean} [options.dismissible=true] - Show dismiss button
 * @returns {string} Toast ID
 */
function show({
  message,
  type = 'info',
  duration = 5000,
  dismissible = true
} = {}) {
  createContainer();

  const id = `toast-${++toastId}`;

  // Create toast element
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.id = id;
  toast.setAttribute('role', 'alert');

  // Icon based on type
  const icons = {
    info: 'ℹ️',
    success: '✓',
    warning: '⚠️',
    error: '✗'
  };

  // Build content
  let html = `
    <span class="toast-icon">${icons[type] || icons.info}</span>
    <span class="toast-message">${escapeHtml(message)}</span>
  `;

  if (dismissible) {
    html += `<button class="toast-close" aria-label="Dismiss">×</button>`;
  }

  toast.innerHTML = html;

  // Add to container
  toastContainer.appendChild(toast);

  // Store reference
  activeToasts.set(id, { element: toast, timeout: null });

  // Add dismiss handler
  if (dismissible) {
    const closeBtn = toast.querySelector('.toast-close');
    closeBtn.addEventListener('click', () => dismiss(id));
    toast.addEventListener('click', (e) => {
      if (e.target === toast) dismiss(id);
    });
  }

  // Animate in
  requestAnimationFrame(() => {
    toast.classList.add('show');
  });

  // Auto-dismiss
  if (duration > 0) {
    const timeout = setTimeout(() => dismiss(id), duration);
    activeToasts.get(id).timeout = timeout;
  }

  return id;
}

/**
 * Dismiss a toast
 * @param {string} id
 */
function dismiss(id) {
  const toast = activeToasts.get(id);
  if (!toast) return;

  // Clear timeout
  if (toast.timeout) {
    clearTimeout(toast.timeout);
  }

  // Animate out
  toast.element.classList.remove('show');
  toast.element.classList.add('hide');

  // Remove from DOM after animation
  setTimeout(() => {
    if (toast.element.parentNode) {
      toast.element.parentNode.removeChild(toast.element);
    }
    activeToasts.delete(id);
  }, 300);
}

/**
 * Dismiss all toasts
 */
function dismissAll() {
  for (const id of activeToasts.keys()) {
    dismiss(id);
  }
}

/**
 * Show info toast
 * @param {string} message
 * @param {Object} [options]
 */
function info(message, options = {}) {
  return show({ message, type: 'info', ...options });
}

/**
 * Show success toast
 * @param {string} message
 * @param {Object} [options]
 */
function success(message, options = {}) {
  return show({ message, type: 'success', ...options });
}

/**
 * Show warning toast
 * @param {string} message
 * @param {Object} [options]
 */
function warning(message, options = {}) {
  return show({ message, type: 'warning', ...options });
}

/**
 * Show error toast
 * @param {string} message
 * @param {Object} [options]
 */
function error(message, options = {}) {
  return show({ message, type: 'error', ...options });
}

/**
 * Escape HTML to prevent XSS
 * @param {string} text
 * @returns {string}
 * @private
 */
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Export for CommonJS
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    show,
    dismiss,
    dismissAll,
    info,
    success,
    warning,
    error
  };
}

// Export for browser
if (typeof window !== 'undefined') {
  window.Toast = {
    show,
    dismiss,
    dismissAll,
    info,
    success,
    warning,
    error
  };
}
