/* global-data-atlas Service Worker
 * 策略：
 *  - /vendor/* 资源：cache-first + stale-while-revalidate（9MB 资源回访秒开，内容指纹 ?v= 变化时自动失效）
 *  - HTML/其他  ：network-first，离线时回退缓存（含 /index.html）
 * 注册：页面 load 后 navigator.serviceWorker.register('sw.js')
 *
 * ⚠️ 2026-10-12 审计修复：缓存无限增长
 *   旧实现 CACHE 名固定且从不清理，而 vendor 引用带 ?v=<md5> 内容指纹 —— 每次部署都会产生
 *   一批新 URL 条目，旧条目永久滞留。13MB 级 vendor 反复累积会逼近浏览器存储配额，
 *   Safari/iOS 配额紧张时可能整站缓存被驱逐（反而失去离线能力）。
 *   现于 activate 阶段做两级清理：
 *     1) 删除非当前版本号的 cache（跨版本升级）
 *     2) 同一 pathname 仅保留指纹最新的条目（淘汰旧 ?v= 版本）
 *   同时：HTML 仅在无查询串时才写入缓存，避免 ?embed=1 / ?year=2020 等状态 URL 各存一份。
 */
const CACHE = 'atlas-v1';
const VENDOR = '/vendor/';

self.addEventListener('install', () => self.skipWaiting());

self.addEventListener('activate', (e) => {
  e.waitUntil((async () => {
    // 1) 跨版本：删除不属于当前版本号的 cache
    const names = await caches.keys();
    await Promise.all(names.filter((n) => n !== CACHE).map((n) => caches.delete(n)));

    // 2) 同版本内：同一 pathname 只保留最新指纹条目
    const cache = await caches.open(CACHE);
    const reqs = await cache.keys();
    const score = (r) => new URL(r.url).searchParams.get('v') || '';   // 无指纹视为最旧
    const keep = new Map();                                            // pathname -> request
    for (const r of reqs) {
      const p = new URL(r.url).pathname;
      const prev = keep.get(p);
      if (!prev) { keep.set(p, r); continue; }
      if (score(r) > score(prev)) { await cache.delete(prev); keep.set(p, r); }
      else { await cache.delete(r); }
    }
    await self.clients.claim();
  })());
});

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
        // 仅缓存无查询串的文档：?embed=1 / ?year=2020 等状态 URL 各存一份会快速膨胀
        if (r && r.ok && url.search === '') cache.put(req, r.clone());
        return r;
      } catch (_) {
        return (await cache.match(req)) || (await cache.match('/index.html')) || Response.error();
      }
    })());
  }
});
