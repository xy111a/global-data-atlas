/* global-data-atlas Service Worker
 * 策略：
 *  - /vendor/* 资源：cache-first + stale-while-revalidate（9MB 资源回访秒开，内容指纹 ?v= 变化时自动失效）
 *  - HTML/其他  ：network-first，离线时回退缓存（含 /index.html）
 * 注册：页面 load 后 navigator.serviceWorker.register('sw.js')
 */
const CACHE = 'atlas-v1';
const VENDOR = '/vendor/';

self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return; // 跨域（CDN/API）不接管

  if (url.pathname.startsWith(VENDOR)) {
    // 资源：先缓存，后台更新
    e.respondWith((async () => {
      const cache = await caches.open(CACHE);
      const cached = await cache.match(req);
      const network = fetch(req).then((r) => {
        if (r && r.ok) cache.put(req, r.clone());
        return r;
      }).catch(() => cached);
      return cached || network;
    })());
  } else {
    // HTML：优先网络，失败回退缓存
    e.respondWith((async () => {
      const cache = await caches.open(CACHE);
      try {
        const r = await fetch(req);
        if (r && r.ok) cache.put(req, r.clone());
        return r;
      } catch (_) {
        return (await cache.match(req)) || (await cache.match('/index.html')) || Response.error();
      }
    })());
  }
});
