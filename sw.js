// 离线缓存：页面走“网络优先”（有新版本就用新的），前端库和 Python 运行环境走“缓存优先”
const VERSION = "tiyan-86050db2d6";
const STATIC = "tiyan-static-pyodide-0.27.7";
const SHELL = ["./", "./index.html", "./manifest.webmanifest", "./icons/icon-192.png",
  "./vendor/codemirror.min.js", "./vendor/python.min.js", "./vendor/runmode.min.js", "./vendor/matchbrackets.min.js",
  "./vendor/closebrackets.min.js", "./vendor/comment.min.js", "./vendor/active-line.min.js", "./vendor/marked.umd.min.js", "./vendor/purify.min.js"];

self.addEventListener("install", e => {
  self.skipWaiting();
  e.waitUntil(caches.open(VERSION).then(c => c.addAll(SHELL)).catch(() => {}));
});
self.addEventListener("activate", e => {
  e.waitUntil((async () => {
    for (const k of await caches.keys()) if (k !== VERSION && k !== STATIC) await caches.delete(k);
    await self.clients.claim();
  })());
});
self.addEventListener("fetch", e => {
  const req = e.request;
  const url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== self.location.origin || url.pathname.includes("/api/")) return;
  if (/\/pyodide\//.test(url.pathname)) { e.respondWith(cacheFirst(req, STATIC)); return; }
  if (/\/(vendor|icons)\//.test(url.pathname)) { e.respondWith(cacheFirst(req, VERSION)); return; }
  e.respondWith(networkFirst(req));
});
async function cacheFirst(req, name) {
  const hit = await caches.match(req);
  if (hit) return hit;
  const res = await fetch(req);
  if (res.ok) (await caches.open(name)).put(req, res.clone());
  return res;
}
async function networkFirst(req) {
  try {
    const res = await fetch(req);
    if (res.ok) (await caches.open(VERSION)).put(req, res.clone());
    return res;
  } catch (e) {
    return (await caches.match(req)) || (await caches.match("./index.html")) || Response.error();
  }
}
