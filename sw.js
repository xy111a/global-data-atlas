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
// atlas-v2 (2026-10-12)：一次性清掉旧 v1 缓存里可能滞留的旧数据文件（如补全前的 us_pop_ts.js）。
// 配合 _headers 将 /vendor/* 改 max-age=0 后，边缘不再供陈旧副本、SW 后台 revalidate 取到新版，
// 主失效机制=版本号 bump（activate 删除非当前 CACHE）+ 边缘强制回源。
const CACHE = 'atlas-v3';
const VENDOR = '/vendor/';

self.addEventListener('install', () => self.skipWaiting());

/* 2026-10-24 审计修复：
   - 旧实现只在 activate 时按 pathname 淘汰，且把 md5 字符串字典序当“最新”；
     两次 SW 版本之间每次部署都会新增一批 ?v 条目，旧条目永久滞留（可达 13MB/次）。
   - 现改为每次写入 vendor 缓存后立即淘汰同 pathname 的旧条目，缓存与当前引用一致；
     activate 只负责清跨版本 cache（保留离线能力）。 */
async function putAndPrune(cache, req, res){
  await cache.put(req, res);
  const path = new URL(req.url).pathname;
  const keys = await cache.keys();
  await Promise.all(keys
    .filter(k => k.url !== req.url && new URL(k.url).pathname === path)
    .map(k => cache.delete(k)));
}

self.addEventListener('activate', (e) => {
  e.waitUntil((async () => {
    const names = await caches.keys();
    await Promise.all(names.filter((n) => n !== CACHE).map((n) => caches.delete(n)));
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
      const network = fetch(req).then(async (r) => {
        if (r && r.ok) { try{ await putAndPrune(cache, req, r.clone()); }catch(_){} }
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
