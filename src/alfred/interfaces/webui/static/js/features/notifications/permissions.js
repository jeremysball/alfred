/**
 * Notification Permission Manager
 *
 * Handles browser notification permission requests and state.
 * Stores permission choice in localStorage for persistence.
 */

const STORAGE_KEY = 'alfred_notification_permission';

/**
 * Get the current notification permission status
 * @returns {NotificationPermission} 'granted', 'denied', 'default', or null (not supported)
 */
function getPermission() {
  if (!('Notification' in window)) {
    return null;
  }
  return Notification.permission;
}

/**
 * Check if notifications are supported
 * @returns {boolean}
 */
function isSupported() {
  return 'Notification' in window;
}

/**
 * Check if permission is granted
 * @returns {boolean}
 */
function isGranted() {
  return getPermission() === 'granted';
}

/**
 * Check if permission is denied
 * @returns {boolean}
 */
function isDenied() {
  return getPermission() === 'denied';
}

/**
 * Check if we should ask for permission
 * @returns {boolean}
 */
function shouldAsk() {
  const permission = getPermission();
  return permission === 'default' || permission === null;
}

/**
 * Request notification permission from user
 * @returns {Promise<NotificationPermission>} The resulting permission
 */
async function request() {
  if (!isSupported()) {
    return null;
  }

  try {
    const result = await Notification.requestPermission();
    savePermissionState(result);
    return result;
  } catch (err) {
    console.error('Failed to request notification permission:', err);
    return 'denied';
  }
}

/**
 * Request permission only if not already decided
 * @returns {Promise<NotificationPermission|null>} Result or null if not needed
 */
async function requestIfNeeded() {
  const current = getPermission();

  if (current === 'granted') {
    return 'granted';
  }

  if (current === 'denied') {
    return 'denied';
  }

  return await request();
}

/**
 * Save permission state to localStorage
 * @param {NotificationPermission} state
 * @private
 */
function savePermissionState(state) {
  try {
    localStorage.setItem(STORAGE_KEY, state);
  } catch (err) {
    console.warn('Failed to save permission state:', err);
  }
}

/**
 * Load permission state from localStorage
 * @returns {NotificationPermission|null}
 * @private
 */
function loadPermissionState() {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch (err) {
    return null;
  }
}

/**
 * Show permission instructions to user
 * @returns {string} Help message
 */
function getInstructions() {
  const browser = detectBrowser();

  const instructions = {
    chrome: 'Click the lock icon in the address bar, then allow notifications.',
    firefox: 'Click the icon in the address bar, then allow notifications.',
    safari: 'Open Safari Preferences > Websites > Notifications, then allow for this site.',
    edge: 'Click the lock icon in the address bar, then allow notifications.',
    default: 'Check your browser settings to allow notifications for this site.'
  };

  return instructions[browser] || instructions.default;
}

/**
 * Detect browser type
 * @returns {string} Browser name
 * @private
 */
function detectBrowser() {
  const ua = navigator.userAgent.toLowerCase();

  if (ua.includes('chrome') && !ua.includes('edg')) return 'chrome';
  if (ua.includes('firefox')) return 'firefox';
  if (ua.includes('safari') && !ua.includes('chrome')) return 'safari';
  if (ua.includes('edg')) return 'edge';

  return 'default';
}

/**
 * Initialize permission manager
 * Loads saved state and checks current permission
 */
function init() {
  if (!isSupported()) {
    console.log('Notifications not supported in this browser');
    return;
  }

  const saved = loadPermissionState();
  const current = getPermission();

  console.log(`Notification permission: ${current} (saved: ${saved})`);
}

// Export for ESM and browser usage
export {
  getPermission,
  isSupported,
  isGranted,
  isDenied,
  shouldAsk,
  request,
  requestIfNeeded,
  getInstructions,
  init
};

if (typeof window !== 'undefined') {
  window.NotificationPermissionManager = {
    getPermission,
    isSupported,
    isGranted,
    isDenied,
    shouldAsk,
    request,
    requestIfNeeded,
    getInstructions,
    init
  };
}
