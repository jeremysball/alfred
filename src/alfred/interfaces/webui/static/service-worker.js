/**
 * Alfred Web UI Service Worker
 *
 * Provides static asset caching and offline support.
 * Scope: Static asset caching only (message queuing deferred to post-MVP)
 */

const CACHE_VERSION = 'v1';
const STATIC_CACHE_NAME = `alfred-static-${CACHE_VERSION}`;

/**
 * Static assets to cache on install
 * These form the "app shell" that loads instantly
 */
const STATIC_ASSETS = [
  '/',
  '/static/index.html',
  '/static/css/base.css',
  '/static/css/themes.css',
  '/static/js/main.js',
  '/static/js/websocket-client.js',
  '/static/js/components/chat-message.js',
  '/static/js/components/code-block.js',
  '/static/js/components/session-list.js',
  '/static/js/components/status-bar.js',
  '/static/js/components/toast-container.js',
  '/static/js/components/tool-call.js',
  '/static/js/features/animations/index.js',
  '/static/js/features/animations/utils.js',
  '/static/js/features/animations/message-animator.js',
  '/static/js/features/animations/typing-indicator.js',
  '/static/js/features/animations/tool-call-progress.js',
  '/static/js/features/animations/skeleton.js',
  '/static/js/features/animations/styles.css',
  '/static/js/features/command-palette/index.js',
  '/static/js/features/command-palette/palette.js',
  '/static/js/features/command-palette/commands.js',
  '/static/js/features/command-palette/fuzzy-search.js',
  '/static/js/features/command-palette/styles.css',
  '/static/js/features/keyboard/index.js',
  '/static/js/features/keyboard/which-key.js',
  '/static/js/features/keyboard/styles.css',
  '/static/js/features/context-menu/index.js',
  '/static/js/features/context-menu/menu.js',
  '/static/js/features/context-menu/message-menu.js',
  '/static/js/features/context-menu/code-menu.js',
  '/static/js/features/context-menu/styles.css',
  '/static/js/features/notifications/index.js',
  '/static/js/features/notifications/service.js',
  '/static/js/features/notifications/permissions.js',
  '/static/js/features/notifications/favicon.js',
  '/static/js/features/notifications/toast.js',
  '/static/js/features/notifications/styles.css',
  '/static/js/features/drag-drop/index.js',
  '/static/js/features/drag-drop/manager.js',
  '/static/js/features/drag-drop/validation.js',
  '/static/js/features/drag-drop/compression.js',
  '/static/js/features/drag-drop/styles.css',
  '/static/js/features/offline/index.js',
  '/static/js/features/offline/connection-monitor.js',
  '/static/js/features/offline/offline-indicator.js',
  '/static/js/features/offline/styles.css',
];

/**
 * Install event: Cache static assets
 */
self.addEventListener('install', (event) => {
  console.log('[SW] Install event');

  event.waitUntil(
    caches.open(STATIC_CACHE_NAME)
      .then((cache) => {
        console.log('[SW] Caching static assets...');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => {
        console.log('[SW] Static assets cached successfully');
        // Skip waiting to activate immediately
        return self.skipWaiting();
      })
      .catch((error) => {
        console.error('[SW] Failed to cache static assets:', error);
      })
  );
});

/**
 * Activate event: Clean up old caches
 */
self.addEventListener('activate', (event) => {
  console.log('[SW] Activate event');

  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((name) => name.startsWith('alfred-static-') && name !== STATIC_CACHE_NAME)
            .map((name) => {
              console.log(`[SW] Deleting old cache: ${name}`);
              return caches.delete(name);
            })
        );
      })
      .then(() => {
        console.log('[SW] Old caches cleaned up');
        // Take control of all clients immediately
        return self.clients.claim();
      })
  );
});

/**
 * Fetch event: Serve from cache, fallback to network
 */
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }

  // Skip WebSocket requests
  if (request.headers.get('upgrade') === 'websocket') {
    return;
  }

  // Skip API/WebSocket endpoints
  if (url.pathname.startsWith('/ws')) {
    return;
  }

  // Strategy: Cache First for static assets
  if (isStaticAsset(url.pathname)) {
    event.respondWith(cacheFirst(request));
    return;
  }

  // Strategy: Network First for HTML (fallback to cache)
  if (request.mode === 'navigate' || request.headers.get('accept')?.includes('text/html')) {
    event.respondWith(networkFirst(request));
    return;
  }

  // Default: Network with cache fallback
  event.respondWith(networkWithCacheFallback(request));
});

/**
 * Check if URL is a static asset
 */
function isStaticAsset(pathname) {
  return pathname.startsWith('/static/') || pathname === '/';
}

/**
 * Cache First strategy: Return cached, fetch in background for update
 */
async function cacheFirst(request) {
  const cache = await caches.open(STATIC_CACHE_NAME);
  const cached = await cache.match(request);

  if (cached) {
    // Return cached immediately, but also fetch for update
    fetch(request)
      .then((response) => {
        if (response.ok) {
          cache.put(request, response.clone());
        }
      })
      .catch(() => {
        // Network failed, cached version is already being served
      });

    return cached;
  }

  // Not in cache, fetch from network
  try {
    const response = await fetch(request);
    if (response.ok) {
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    console.error('[SW] Fetch failed:', error);
    // Return a fallback response for critical assets
    if (request.url.endsWith('.html') || request.url === '/') {
      return new Response(
        '<h1>Offline</h1><p>Please check your connection.</p>',
        { headers: { 'Content-Type': 'text/html' } }
      );
    }
    throw error;
  }
}

/**
 * Network First strategy: Try network, fallback to cache
 */
async function networkFirst(request) {
  const cache = await caches.open(STATIC_CACHE_NAME);

  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    console.log('[SW] Network failed, serving from cache:', request.url);
    const cached = await cache.match(request);
    if (cached) {
      return cached;
    }
    // Return offline fallback
    return new Response(
      `<!DOCTYPE html>
<html>
<head><title>Alfred - Offline</title></head>
<body style="font-family: system-ui, sans-serif; padding: 2rem; text-align: center;">
  <h1>You're offline</h1>
  <p>The Alfred Web UI is loading from cache.</p>
  <p>Some features may be unavailable until you reconnect.</p>
  <button onclick="window.location.reload()" style="padding: 0.5rem 1rem; cursor: pointer;">
    Try Again
  </button>
</body>
</html>`,
      {
        headers: { 'Content-Type': 'text/html' },
        status: 200,
        statusText: 'OK (Offline)'
      }
    );
  }
}

/**
 * Network with cache fallback
 */
async function networkWithCacheFallback(request) {
  try {
    return await fetch(request);
  } catch (error) {
    const cache = await caches.open(STATIC_CACHE_NAME);
    const cached = await cache.match(request);
    if (cached) {
      return cached;
    }
    throw error;
  }
}

/**
 * Message event: Handle communication from main thread
 */
self.addEventListener('message', (event) => {
  if (event.data?.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }

  if (event.data?.type === 'GET_VERSION') {
    event.ports[0].postMessage({ version: CACHE_VERSION });
  }
});

console.log('[SW] Service worker loaded');
