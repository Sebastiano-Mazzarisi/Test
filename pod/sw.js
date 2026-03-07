const CACHE = 'podputignano-v1';
const ASSETS = ['./index.html', './manifest.json', './icon-192.png', './icon-512.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)));
});

self.addEventListener('fetch', e => {
  // Per l'MP3 vai sempre in rete (contenuto aggiornato ogni 15 min)
  if (e.request.url.endsWith('.mp3')) return;
  e.respondWith(
    caches.match(e.request).then(r => r || fetch(e.request))
  );
});
