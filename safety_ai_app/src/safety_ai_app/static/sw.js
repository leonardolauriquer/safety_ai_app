/* SafetyAI Service Worker
 * Scope: /app/static/ (Streamlit static file serving path)
 * Provides: static-asset caching for performance + install prompt support.
 *
 * Note: navigation-mode fetch interception (offline fallback page) requires
 * the SW to control the app root (/). In Streamlit, static files are served
 * under /app/static/, so the default scope is /app/static/ and navigate
 * events for the main app URL are NOT intercepted here. For full offline
 * navigation support in production, configure the reverse proxy (nginx /
 * Cloud Run) to serve sw.js at / with the Service-Worker-Allowed: / header.
 */

const CACHE_NAME = 'safetyai-shell-v2';

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then(() => Promise.resolve()));
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

  if (url.hostname !== self.location.hostname) return;

  if (!url.pathname.startsWith('/app/static/')) return;

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
