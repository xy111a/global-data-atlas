# Global Data Atlas · 多角度审计报告（2026-10-12 v2）

- **对象**：`global-data-atlas` 活跃副本 = `WorkBuddy/2026-10-06-14-57-44/global-data-atlas`，HEAD `3534505`，与 GitHub `refs/heads/main`（`3534505699…`）逐字一致
- **线上**：https://atlas.huajun.wang（Cloudflare Pages）
- **性质**：**只读审计**，未改动任何源码/数据/配置。修复选项列出但交使用者拍板
- **方法**：全量门禁真实复现（含无头浏览器）+ 生产 HTTP 响应头/缓存头实测 + 数据文件独立重算（不信 `data_verify.py`）+ dist↔源码逐字节核对 + 静态安全/逻辑审查
- **分级**：P0 数据/结论错误 · P1 功能失效或安全缺陷 · P2 明显缺陷 · P3 改进 · OK 已验证

---

## 一句话结论

**项目整体健康（门禁 23/23、数据声明无夸大、无可达 XSS），但有一个真实存在、此刻线上可复现的缺陷：今天 12:08 部署的「美国人口逐年」数据修复，对新访客完全不可见——边缘缓存还在供旧数据。** 根因是缓存失效机制只护住了 `app-core.js`/`meta.js`，没护住会随刷新变化的**数据集文件**；这是上轮「测试环境≠生产环境」元问题的**又一实例**，且 23/23 门禁结构上抓不到它。

---

## 发现与证据

### P1/P2 · 数据集刷新后，部署对用户延迟生效（边缘 4h + SW cache-first），此刻线上正在发生

| 项 | 内容 |
|---|---|
| 现象 | 线上 `/vendor/us_pop_ts.js` 首个州只有 `2020,2025`（稀疏=修复前）；已提交/部署的 `dist/vendor/us_pop_ts.js` 是 `2020,2021,2022,2023,2024,2025`（逐年=修复后）。**部署了，但没到达用户** |
| 直接证据 | `curl -D- https://atlas.huajun.wang/vendor/us_pop_ts.js` → `cf-cache-status: HIT`、`age: 6864`、`cache-control: public, max-age=14400, must-revalidate`。边缘命中约 1.9h 前的旧副本，还要约 2h 才回源 |
| 根因 | `_headers` 对 `/vendor/*` 统一 `max-age=14400`（4h）；而 `build.sh` **只给 `app-core.js`、`meta.js` 注入 `?v=` 内容指纹**。数据集文件（`us_pop_ts.js`/`jp_ts.js`/`countries_wb.js`/`ext_indicators.js`/`cn/*`/`eu/*`…）URL 恒定 → 内容变了 URL 不变 → 4h 内不失效 |
| 反证（部署确实发生） | 带指纹的 `app-core.js` 线上内容 md5 = 本地 dist = `dd07f6f1…`（当前版）。指纹文件走新 URL 立即更新，无指纹文件走旧 URL 未更新——这一非对称正说明「指纹机制有效、只是没覆盖数据文件」 |
| 加重因子（Service Worker） | `sw.js` 中 `CACHE='atlas-v1'` **固定、不随部署变**；`/vendor/*` 是 **cache-first**：SW 先返回自身缓存的旧副本，仅后台 re-fetch 更新，而后台 fetch 又撞上同样的 4h 边缘缓存 → 实际陈旧期可比 4h 更久（回访用户当次拿旧的，下一次才可能刷新） |
| 后果 | 主打「数据诚实性」的产品，about 新鲜度表（meta，指纹新鲜）宣称美国人口「2020–2025 逐年」，而地图实际取到的 `us_pop_ts.js`（无指纹、边缘旧）仍是 `2020+2025` → **标签与真实供的数据此刻相互矛盾** |
| 普遍性 | 这**不是美国人口专属**：今后每一次数据集刷新都会复现同样问题（数据刷新是本项目的常态活动） |
| 复现命令 | `curl -s https://atlas.huajun.wang/vendor/us_pop_ts.js \| grep -o '2020\|2021\|2025' \| sort -u`（线上仅 2020/2025）对比 `dist/vendor/us_pop_ts.js`（含 2021–2024） |

**为什么 23/23 门禁抓不到**：`run_all_tests.sh` 全部对着**本地文件**做断言（数据自洽/渲染/导出/嵌入），从不模拟「部署 → 边缘缓存命中 → SW 命中」这条真实分发链路。属于典型门禁盲区，与上轮 visualMap「配置存在≠组件注册」、嵌入「本地探针不带 CF 头」是同一类元问题。

**修复选项（择一即可，建议 ①，未执行）**：
1. **给所有数据集文件也注入 `?v=` 内容指纹**：把 `build.sh` 的指纹注入从「仅 app-core/meta」推广到全部 `/vendor/*.js`（数据文件）。内容变→URL 变→同时绕过边缘 4h 与 SW cache-first，最贴合现有设计、可自愈。
2. **部署即 bump SW `CACHE` 版本号**（如 `atlas-<git短sha>`），强制 activate 清理并回源。
3. **给会随刷新变化的数据文件单列 `_headers` 规则**：`max-age=0, must-revalidate`（或 `no-cache`），仅对 echarts/world 等大而不变的资源保留长 `max-age`。

---

### P3 · 其余观察项（不阻断，建议顺手处理）

- **指纹哈希算法随构建机漂移**：`build.sh` 的 `HASH()` 回退链是 `md5 → md5sum → shasum -a 1`。实测当前 dist 的 `app-core.js?v=2314f7a7` 其实是该文件的 **sha1 前 8 位**（md5 前 8 位应为 `dd07f6f1`）——说明生成指纹的那台机器 `md5`/`md5sum` 都不可用、落到了 `shasum`。功能上仍「内容变则 token 变」，但跨机不确定、易踩坑。**建议**：`HASH()` 显式统一为一种（如 `openssl dgst -md5`）。
- **SW activate 清理用字典序比指纹**：`score(r)=?v` 后 `if (score(r) > score(prev))` 是按字符串比较挑「字典序更大」的指纹，不是「更新」的；一旦 md5/sha1 token 混用，可能删错条目。当前每个无指纹 pathname 只有一条、影响有限，属潜在逻辑缺陷。
- **出站 `postMessage(state, "*")`**（`global-data-atlas.html:97`）向任意父页广播视图状态（层级/指标/年份/配色）。内容非敏感、已注释说明，可接受；如要收紧可只在同源/已授权 origin 下广播。
- **dist 存在三份同尺寸 HTML**（`index.html`/`global-data-atlas.html`/`embed.html` 均 113090B）。`embed.html` 是主文件的逐字节拷贝，仅为让 `_headers` 命中 `/embed` 路径套不同 CSP（设计使然，运行时靠 `?embed=1` 精简）。上轮记为「index 与 main 重复」，实为 3× 重复，部署体积影响可忽略。
- **`/embed` 仍继承 `X-Frame-Options: SAMEORIGIN`**：跨域嵌入靠「CSP `frame-ancestors` 优先于 XFO」这条**现代浏览器**规则放行；忽略 `frame-ancestors` 的旧浏览器会拒绝嵌入。主流场景无碍；若要覆盖旧浏览器，可在 `/embed` 路径不输出 XFO。

---

## 已验证无问题（OK）

| 维度 | 结论 |
|---|---|
| 全量门禁 | `run_all_tests.sh` **23/23 端到端通过**（含真实浏览器：L3q 嵌入 19/19、L3s 导出 16/16、L3r 欧盟多年 10/10、L3j 视觉回归） |
| 数据声明诚实性 | **独立重算与 meta/FEATURES 一致、无夸大**：WB 214 国(≤2024)、EXT 230、CN 31 省(≤2025)、US_TS 60 区(≤2024)、US_POP_TS 52(≤2025)、JP_TS 47(≤2022)、CITY 321(2023 快照)、CITY_TS 46 城(≤2020) |
| 美国人口修复本身 | `dist`/源码数据**确实已逐年**（2020–2025），修复无误——问题只在分发缓存 |
| dist↔源码同步 | 顶层 14 个 vendor `.js` 逐字节一致、`cn/37`、`eu/28` 文件数对齐；HTML 仅差 `?v=` 注入（+11~22B），非陈旧漂移 |
| 安全头基线 | CSP / `X-Content-Type-Options: nosniff` / Referrer-Policy / Permissions-Policy / HSTS 均在位；主站仍 `SAMEORIGIN` |
| XSS | **无可达注入**：URL hash 的 `sel`/`k` 仅当**查表键**（`COUNTRIES.find(x=>x[2]===k)`、`US_STATES_GDP[k]`…命中才渲染），回显名称一律走 `textContent`/`esc()`（`esc` 定义于 `app-core.js:239`）；`showBanner` 用 `textContent` |
| 选择器注入 | 已修：`setMetric`/排行用字面选择器（如 `button[data-m="gdp"]`），无字符串拼接外部输入 |
| postMessage 来源 | 已修：先校 `d.type==='atlas:cmd'`，再 `atlasOriginAllowed(e.origin)`，跨域非白名单回 `atlas:error` |
| SEO/路由 | robots 屏蔽 `/atlas_test/`、sitemap 三主页（未收 `/embed`，正确）、未知路径回 404 |

---

## 覆盖度声明（本轮审了什么 / 没审什么）

**已实测**：门禁 23 步全跑；线上 `/`、`/embed`、`/embed.html`、vendor 多个资源的响应头与缓存头；`us_pop_ts`/`jp_ts`/`echarts`/`countries_wb`/`app-core` 线上↔本地逐字节；数据覆盖数与最大年独立重算；app-core.js + 主 HTML 的安全 sink 与 hash 恢复路径静态审查。

**未独立验证（诚实标注，别当「没问题」）**：
- 欧盟 242 大区计数：我的 vm harness 未能展开 `eu_metrics.js` 结构，此数依赖门禁 L3r + `data_verify.py`，本轮**未独立复核**。
- 汇率折算/增长口径的具体数值：仅通过 `growth_currency_test`（30 断言绿），未另行人工复算。
- 真实浏览器跨域 iframe 嵌入生产站：本轮只验了响应头（CSP/XFO 并存），实际渲染握手依赖门禁 L3q 与上轮实测。
- 数据陈旧缺陷只**实证了 `us_pop_ts`（今日唯一变更项）**；同类风险对所有数据集文件成立但未逐一演示。
- Cloudflare 部署日志本地不可见：「已部署但边缘缓存」的判定基于「指纹文件新 / 无指纹文件旧」的非对称推断（app-core 为新即证明部署发生），未见 deploy 事件本身。
- 移动端响应式、无障碍键盘路径：未在本轮重测，依赖门禁 L3j/L3p。
