/**
 * Notification Service
 *
 * Handles showing browser notifications when responses complete
 * while the tab is not focused.
 */

import { isGranted, isSupported } from "./permissions.js";

/**
 * Show a browser notification
 * @param {Object} options
 * @param {string} options.title - Notification title
 * @param {string} options.body - Notification body text
 * @param {string} [options.icon] - Icon URL
 * @param {string} [options.tag] - Notification tag for grouping
 * @param {Object} [options.data] - Additional data
 * @returns {Promise<Notification|null>} The notification object or null
 */
async function show({
  title = "Alfred",
  body,
  icon = "/static/icons/icon-192x192.png",
  tag = "alfred-response",
  data = {},
} = {}) {
  if (!isSupported || !isGranted()) {
    return null;
  }

  try {
    const notification = new Notification(title, {
      body,
      icon,
      tag,
      data,
      requireInteraction: false,
      silent: false,
    });

    // Handle click - focus the window
    notification.onclick = () => {
      window.focus();
      notification.close();

      // Dispatch event for other handlers
      window.dispatchEvent(
        new CustomEvent("notification:click", {
          detail: { notification, data },
        }),
      );
    };

    // Auto-close after 10 seconds
    setTimeout(() => {
      notification.close();
    }, 10000);

    return notification;
  } catch (err) {
    console.error("Failed to show notification:", err);
    return null;
  }
}

/**
 * Show notification for a completed response
 * @param {string} preview - Message preview text
 * @param {Object} [options] - Additional options
 */
async function showResponseComplete(preview, options = {}) {
  const title = options.title || "Response ready from Alfred";
  const body = preview
    ? preview.slice(0, 100) + (preview.length > 100 ? "..." : "")
    : "Your message has been answered";

  return await show({
    title,
    body,
    tag: `alfred-response-${Date.now()}`,
    data: { type: "response-complete", ...options.data },
  });
}

/**
 * Show notification when tab is hidden
 * @param {string} message - The notification message
 * @returns {Promise<boolean>} True if notification was shown
 */
async function notifyIfHidden(message) {
  // Only show if tab is hidden
  if (!document.hidden) {
    return false;
  }

  // Only show if permission granted
  if (!isGranted()) {
    return false;
  }

  const notification = await showResponseComplete(message);
  return notification !== null;
}

/**
 * Check if Do Not Disturb is enabled (macOS)
 * @returns {boolean}
 */
function isDoNotDisturbEnabled() {
  // There's no standard API for DND, but we can check if notifications
  // were recently denied or if the user has a preference set
  try {
    const dnd = localStorage.getItem("alfred_dnd_mode");
    return dnd === "true";
  } catch {
    return false;
  }
}

/**
 * Set Do Not Disturb mode
 * @param {boolean} enabled
 */
function setDoNotDisturb(enabled) {
  try {
    localStorage.setItem("alfred_dnd_mode", enabled ? "true" : "false");
  } catch (err) {
    console.warn("Failed to save DND state:", err);
  }
}

// Export for ESM and browser
export { isDoNotDisturbEnabled, notifyIfHidden, setDoNotDisturb, show, showResponseComplete };

if (typeof window !== "undefined") {
  window.NotificationService = {
    show,
    showResponseComplete,
    notifyIfHidden,
    isDoNotDisturbEnabled,
    setDoNotDisturb,
  };
}
