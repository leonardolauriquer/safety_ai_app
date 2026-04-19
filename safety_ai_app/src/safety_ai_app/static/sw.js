/* SafetyAI Service Worker — network-first com fallback offline */
const CACHE_NAME = 'safetyai-shell-v1';

const OFFLINE_HTML = `<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SafetyAI — Offline</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      min-height: 100vh; display: flex; align-items: center; justify-content: center;
      background: #020617; color: #F1F5F9; font-family: -apple-system, BlinkMacSystemFont, 'Inter', sans-serif;
      padding: 24px;
    }
    .card {
      background: rgba(15,23,42,0.85); border: 1px solid rgba(74,222,128,0.3);
      border-radius: 20px; padding: 40px 32px; max-width: 400px; width: 100%; text-align: center;
      box-shadow: 0 0 40px rgba(74,222,128,0.15);
    }
    .icon { font-size: 3rem; margin-bottom: 16px; }
    h1 { font-size: 1.5rem; color: #4ADE80; margin-bottom: 12px; letter-spacing: 0.05em; }
    p { color: #94A3B8; line-height: 1.6; margin-bottom: 24px; }
    button {
      background: linear-gradient(135deg, #4ADE80, #22D3EE); border: none; border-radius: 10px;
      color: #020617; font-weight: 700; padding: 12px 28px; font-size: 1rem; cursor: pointer;
    }
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">🛡️</div>
    <h1>SafetyAI — Offline</h1>
    <p>Sem conexão com a internet. Reconecte-se para usar o assistente de SST.</p>
    <button onclick="window.location.reload()">Tentar novamente</button>
  </div>
</body>
</html>`;

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.put('/__offline__', new Response(OFFLINE_HTML, {
        headers: { 'Content-Type': 'text/html; charset=utf-8' }
      }));
    })
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

  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request).catch(() =>
        caches.match('/__offline__').then((r) => r || new Response(OFFLINE_HTML, {
          headers: { 'Content-Type': 'text/html; charset=utf-8' }
        }))
      )
    );
    return;
  }

  if (url.hostname !== self.location.hostname) return;

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        if (response.ok && !url.pathname.startsWith('/stream')) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        }
        return response;
      })
      .catch(() => caches.match(event.request))
  );
});
