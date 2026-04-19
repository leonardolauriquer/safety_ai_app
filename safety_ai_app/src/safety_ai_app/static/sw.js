/* SafetyAI Service Worker
 * Served at /sw.js by server.py proxy with Service-Worker-Allowed: / header.
 * Scope: / (controls entire app origin).
 * Provides: offline navigation fallback + static asset caching.
 */

const CACHE_NAME = 'safetyai-shell-v3';
const OFFLINE_URL = '/_safetyai_offline';

self.addEventListener('install', (event) => {
  event.waitUntil(
    fetch(OFFLINE_URL)
      .then((res) => caches.open(CACHE_NAME).then((cache) => cache.put(OFFLINE_URL, res)))
      .catch(() => Promise.resolve())
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;

  const url = new URL(event.request.url);

  /* Navigation: network-first, fall back to offline page */
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request).catch(() =>
        caches.match(OFFLINE_URL).then(
          (r) => r || new Response('<h1>Offline</h1>', { headers: { 'Content-Type': 'text/html' } })
        )
      )
    );
    return;
  }

  /* Same-origin static assets: network-first with cache fallback */
  if (url.hostname !== self.location.hostname) return;

  /* Skip Streamlit WebSocket/stream paths */
  if (url.pathname.startsWith('/stream') || url.pathname.startsWith('/_stcore')) return;

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        if (response.ok) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        }
        return response;
      })
      .catch(() => caches.match(event.request))
  );
});
