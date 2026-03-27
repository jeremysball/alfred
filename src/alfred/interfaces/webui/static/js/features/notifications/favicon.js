/**
 * Favicon Badge
 *
 * Shows unread message count on the favicon.
 * Updates when tab is hidden, clears when tab becomes visible.
 */

let unreadCount = 0;
let originalFavicon = null;
let canvas = null;
let ctx = null;
let linkElement = null;

/**
 * Initialize favicon badge system
 * Captures the original favicon for restoration
 */
function init() {
  // Find the favicon link element
  linkElement = document.querySelector('link[rel="icon"]') ||
                document.querySelector('link[rel="shortcut icon"]');

  if (!linkElement) {
    console.warn('No favicon link element found');
    return;
  }

  // Store original favicon
  originalFavicon = linkElement.href;

  // Create canvas for badge drawing
  canvas = document.createElement('canvas');
  canvas.width = 32;
  canvas.height = 32;
  ctx = canvas.getContext('2d');

  // Listen for visibility changes
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) {
      // Tab became visible - clear badge
      clear();
    }
  });
}

/**
 * Draw badge on favicon
 * @param {number} count
 * @private
 */
function drawBadge(count) {
  if (!ctx || !canvas) return;

  // Clear canvas
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // Load original favicon
  const img = new Image();
  img.crossOrigin = 'anonymous';
  img.onload = () => {
    // Draw original favicon
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

    if (count > 0) {
      // Draw badge circle
      const badgeSize = 16;
      const x = canvas.width - badgeSize;
      const y = canvas.height - badgeSize;

      // Badge background
      ctx.fillStyle = '#f85149'; // Red badge
      ctx.beginPath();
      ctx.arc(x + badgeSize/2, y + badgeSize/2, badgeSize/2, 0, Math.PI * 2);
      ctx.fill();

      // Badge text
      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 10px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';

      const text = count > 99 ? '99+' : count.toString();
      const fontSize = count > 9 ? 8 : 10;
      ctx.font = `bold ${fontSize}px sans-serif`;

      ctx.fillText(text, x + badgeSize/2, y + badgeSize/2 + 1);
    }

    // Update favicon
    updateFaviconLink(canvas.toDataURL('image/png'));
  };

  img.onerror = () => {
    console.warn('Failed to load original favicon');
  };

  img.src = originalFavicon;
}

/**
 * Update favicon link element
 * @param {string} dataUrl
 * @private
 */
function updateFaviconLink(dataUrl) {
  if (!linkElement) return;

  // Create new link element
  const newLink = document.createElement('link');
  newLink.rel = 'icon';
  newLink.type = 'image/png';
  newLink.href = dataUrl;

  // Remove old and add new
  const oldLink = document.querySelector('link[rel="icon"]') ||
                  document.querySelector('link[rel="shortcut icon"]');
  if (oldLink) {
    oldLink.parentNode.removeChild(oldLink);
  }

  document.head.appendChild(newLink);
  linkElement = newLink;
}

/**
 * Set the unread count badge
 * @param {number} count
 */
function set(count) {
  unreadCount = count;

  // Only show badge when tab is hidden
  if (!document.hidden) {
    return;
  }

  drawBadge(count);
}

/**
 * Increment unread count
 * @param {number} [amount=1]
 */
function increment(amount = 1) {
  set(unreadCount + amount);
}

/**
 * Clear the badge
 */
function clear() {
  unreadCount = 0;
  if (originalFavicon) {
    updateFaviconLink(originalFavicon);
  }
}

/**
 * Get current unread count
 * @returns {number}
 */
function getCount() {
  return unreadCount;
}

// Export for CommonJS
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    init,
    set,
    increment,
    clear,
    getCount
  };
}

// Export for browser
if (typeof window !== 'undefined') {
  window.FaviconBadge = {
    init,
    set,
    increment,
    clear,
    getCount
  };
}
