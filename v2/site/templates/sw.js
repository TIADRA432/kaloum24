/* Service worker Kaloum24 : on ne met jamais en cache l'admin ni les recherches ; pages vues = lisibles hors ligne. */
const VERSION = "k24-{{ version }}";
const PRECACHE = {{ precache|safe }};
const SECOURS = "/hors-ligne/";
const MAX_PAGES = 40;

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(VERSION).then((c) => c.addAll([SECOURS, ...PRECACHE])).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((cles) => Promise.all(cles.filter((c) => c !== VERSION).map((c) => caches.delete(c)))).then(() => self.clients.claim()));
});

const EXCLUS = [/^\/admin\//, /^\/django-admin\//, /^\/search\//, /^\/sw\.js$/, /^\/documents\//, /^\/healthz/];

async function limiter(cache) {
  const cles = await cache.keys();
  const pages = cles.filter((r) => !r.url.includes("/static/"));
  if (pages.length > MAX_PAGES) await cache.delete(pages[0]);
}

self.addEventListener("fetch", (e) => {
  const req = e.request;
  const url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== self.location.origin || EXCLUS.some((re) => re.test(url.pathname))) return;

  if (req.mode === "navigate") {
    e.respondWith((async () => {
      try {
        const rep = await fetch(req);
        if (rep.ok) { const c = await caches.open(VERSION); c.put(req, rep.clone()); limiter(c); }
        return rep;
      } catch (_) {
        return (await caches.match(req)) || (await caches.match(SECOURS)) || Response.error();
      }
    })());
    return;
  }

  if (url.pathname.startsWith("/static/")) {
    e.respondWith(caches.match(req).then((hit) => hit || fetch(req).then((rep) => {
      if (rep.ok) { const copie = rep.clone(); caches.open(VERSION).then((c) => c.put(req, copie)); }
      return rep;
    })));
  }
});
