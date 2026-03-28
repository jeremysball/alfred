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

// Import from window globals set up by individual modules
const NotificationPermissionManager = window.NotificationPermissionManager || {};
const NotificationService = window.NotificationService || {};
const FaviconBadge = window.FaviconBadge || {};
const Toast = window.Toast || {};

// Re-export everything
const NotificationsLib = {
  NotificationPermissionManager,
  NotificationService,
  FaviconBadge,
  Toast,
};

// Export for ES modules
export {
  FaviconBadge,
  NotificationPermissionManager,
  NotificationService,
  NotificationsLib,
  Toast,
};

// Also expose on window
if (typeof window !== "undefined") {
  window.NotificationsLib = NotificationsLib;
}
