/**
 * Offline Feature Module
 *
 * Service Worker integration, connection monitoring, and offline indicator.
 *
 * @example
 * import { ConnectionMonitor, OfflineIndicator } from './features/offline/index.js';
 *
 * const monitor = new ConnectionMonitor();
 * monitor.trackWebSocket(wsClient);
 */

export { ConnectionMonitor } from './connection-monitor.js';
export { OfflineIndicator } from './offline-indicator.js';

