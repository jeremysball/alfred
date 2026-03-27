/**
 * Notifications Module
 *
 * Browser notifications, favicon badges, and toast notifications.
 *
 * Usage:
 *   import { NotificationPermissionManager, NotificationService, FaviconBadge, Toast } from './notifications/index.js';
 *
 *   // Request permission
 *   const permission = await NotificationPermissionManager.request();
 *
 *   // Show notification
 *   await NotificationService.showResponseComplete('Hello world');
 *
 *   // Update favicon badge
 *   FaviconBadge.increment();
 *
 *   // Show toast
 *   Toast.info('Notifications enabled');
 */

// Import modules (works with both CommonJS and browser globals)
const permissions = typeof require !== 'undefined' ? require('./permissions.js') : (window.NotificationPermissionManager || {});
const service = typeof require !== 'undefined' ? require('./service.js') : (window.NotificationService || {});
const favicon = typeof require !== 'undefined' ? require('./favicon.js') : (window.FaviconBadge || {});
const toast = typeof require !== 'undefined' ? require('./toast.js') : (window.Toast || {});

// Export for CommonJS
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    NotificationPermissionManager: permissions,
    NotificationService: service,
    FaviconBadge: favicon,
    Toast: toast
  };
}

// Export for ES modules
export {
  permissions as NotificationPermissionManager,
  service as NotificationService,
  favicon as FaviconBadge,
  toast as Toast
};

// Also expose on window
if (typeof window !== 'undefined') {
  window.NotificationsLib = {
    NotificationPermissionManager: permissions,
    NotificationService: service,
    FaviconBadge: favicon,
    Toast: toast
  };
}
