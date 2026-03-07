const CACHE = 'podputignano-v2';
const ASSETS = ['./manifest.json', './icon-192.png', './icon-512.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  // Elimina vecchie cache
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  const url = e.request.url;

  // index.html: sempre dalla rete, mai dalla cache
  if (url.includes('index.html') || e.request.mode === 'navigate') {
    e.respondWith(fetch(e.request, { cache: 'no-store' }));
    return;
  }

  // MP3: sempre dalla rete (contenuto aggiornato frequentemente)
  if (url.endsWith('.mp3')) {
    e.respondWith(fetch(e.request));
    return;
  }

  // Altri asset (icone, manifest): cache first
  e.respondWith(
    caches.match(e.request).then(r => r || fetch(e.request))
  );
});
