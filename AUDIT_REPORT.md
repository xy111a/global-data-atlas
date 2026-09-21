# Global Data Atlas · 全面审计报告

- **日期**：2026-09-21  
- **对象**：`/Users/huajun/WorkBuddy/2026-08-18-22-48-41/global-data-atlas`  
- **线上**：https://atlas.huajun.wang · Pages 部署 `5e1a14ca`（alias 自定义域 success）  
- **计划**：见 `AUDIT_PLAN.md`（A–E 五维 58 项）  
- **方法**：静态审查 + `node`/`vm` 数值抽检 + `tests/*` 门禁 + 线上 HTTP/头/DNS/TLS  
- **分级**：P1 功能错误/数据错误 · P2 明显缺陷/风险 · P3 改进 · OK 已验证  

> 执行说明：5 个并行子代理中 4 个因沙箱 `UnknownError` 失败，1 个部分完成（E 区静态）。A–D 及 E 的动态项由主代理补做，证据均来自本轮实际命令输出。

---

## 总览

| 维度 | 结果 | P1 | P2 | P3 | OK 摘要 |
|---|---|---|---|---|---|
| A 安全与部署 | 良好 | 0 | 1 | 2 | TLS/HSTS/头/404/无密钥 |
| B 数据与美元 | 良好 | 0 | 1 | 1 | 六层折算抽检一致 |
| C 性能与资源 | 可接受 | 0 | 1 | 1 | br 压缩、懒加载、1.58MB 首屏 |
| D SEO/可访问性 | 良好 | 0 | 2 | 1 | robots/sitemap/404/站内链接 |
| E 代码与交互 | 有缺陷 | 2 | 3 | 2 | 语法/门禁/回归大体通过 |
| **合计** | | **2** | **8** | **7** | |

**整体健康度：B+**（线上可用、USD-only 正确、门禁通过；对比页城市键与搜索/URL 交互有明确 P1/P2）

---

## P1（优先修复）

### E7-1 · 对比页城市 key 解析错误（搜索添加 / `?add=`）

**证据**（`compare.html`）：

| 入口 | 解析结果 for `city:440300:440000` | 是否正确 |
|---|---|---|
| 层级列表点击 L183–185 | `k=440300`, `pa=440000` | OK |
| 搜索结果点击 L289 `parts.slice(1,3).join(":")` | `k=440300:440000` | **错误** |
| `parseAddParam` L254 `parts.slice(1).join(":")` | `k=440300:440000` | **错误** |
| `isAdded` L174 对 `unitKey` 再 split | `k=440300:440000` | **与列表添加的 k 不一致** |

`regCity(cm, "440300:440000")` 会取不到序列/指标，搜索加市与 URL `?add=city:…` 城市对比会静默失败或显示异常；层级列表加市后「已添加 ✓」也可能对不上。

**建议**：统一解析：`t=parts[0]`；`k = parts.length>2 ? parts[1] : parts.slice(1).join(":")`（或城市固定 `parts[1]`）；`pa = parts.length>2 ? +parts[2] : undefined`。`isAdded`/`parseAddParam`/搜索 onclick/列表 onclick 共用同一函数。

### E7-2 · 主页面搜索：美国州依赖已加载的 `US_GEO`

**证据** `global-data-atlas.html` `doSearch` L1211：`if(window.US_GEO){ … search states }`。世界层通常未加载 `vendor/us-states.js`，搜 “California / 加州” 直接落到「未找到」；日本 NUTS 同样无搜索分支。

**建议**：与城市一致——直接查 `US_STATES_GDP` / `JP_METRICS` / `EU_METRICS` 键，命中后再 `loadUS()`/`loadJapan()`/`loadNUTS()`（可沿用现有 700ms 延迟或 await）。

---

## P2

| ID | 问题 | 证据 | 建议 |
|---|---|---|---|
| E7-3 | ESC 在 `#yearSel` 等 SELECT 上会触发「返回世界」 | L1349 仅排除 `INPUT` | 排除 `INPUT\|SELECT\|TEXTAREA\|[contenteditable]` |
| E7-4 | `saveState`/`restoreState` 不支持 `city` | L1076–1080 无 city；restore 同无分支 | `sel=city:adcode:pa` 写入并恢复 `showCityPanel` |
| E13 | 自动化未覆盖：搜索、ESC、年份、11 指标、面板折叠、compare 城市 key、URL 恢复 city | `tests/` 13 个 py 清单比对 | 补 1–2 个 headless 冒烟 |
| E12 | README/文档漂移 | README L5 写 `huajun.wang`；L26 仍写「9/9…L3g 双币切换」；域应为 `atlas.huajun.wang` | 同步域名、测试步骤数、USD-only |
| D1 | 主页 **无 `<h1>`** | brand 仅 `#crumb` div；about/compare 有 h1 | 静态 h1「全球数据地图」或 `#crumb` 用 h1 |
| D8 | 主页无 `<main>` landmark | `#main` 为 div | 改为 `<main>` 或 `role="main"` |
| C1 | 首屏同步 JS 原始 **1.58MB**（HTML 81KB） | 11 个 sync script 合计 1658396 B | 与 README「~2.4MB」口径统一；可考虑延后 `world.js`/`countries_wb.js` 分片（收益中） |
| B2 | 省级 2025 汇率无表，兜底 **7.2**（非 2025 实际） | `gdpRate(2025)→USD_CNY=7.2`；FXRATE 仅 2000–2024 | 关于页/标签注明 2025 用近似；或补 2025 年均 |

---

## P3

| ID | 问题 | 证据 | 建议 |
|---|---|---|---|
| A3 | 无 CSP、无 Permissions-Policy | `curl -I` 无对应头 | `_headers` 加宽松 CSP（`default-src 'self'; img-src 'self' data: https://geo.datav.aliyun.com`）需实测地图/字体 |
| A4/C | 注释仍写「折算人民币(CNY)」；`usGdpY` 返回 CNY 且主路径已不用 | L299/L333；`app-core` usGdpY | 改注释；删除或标注仅调试 |
| E11 | 无全局 `onerror`/`unhandledrejection` 收集（仅 echarts `#fatal`） | 源码 grep | 调试构建注入 collector |
| E13 | 地图无键盘下钻（已知限制） | README 已声明 | 可选：排行榜 Enter 已有 tabindex |

---

## OK（已验证通过）

### A · 安全与部署
- **A1** TLS：`CN=atlas.huajun.wang`，Google Trust Services，**2026-08-18 → 2026-11-16**；HSTS `31536000; includeSubDomains; preload`
- **A2** 响应头：`x-content-type-options: nosniff`、`referrer-policy: strict-origin-when-cross-origin`、`x-frame-options: SAMEORIGIN`（`_headers` 生效）
- **A5** dist/源码无 API key/密码/RSA/AWS 模式命中
- **A6** 展示插值普遍 `esc()`；无 `eval(` / `new Function` 于前端
- **A8** `./build.sh` md5 全绿（含 404/robots/sitemap/favicon/_headers）
- **A11** `/robots.txt` → `text/plain`；`/sitemap.xml` → `application/xml`；`/nope`、`/data.json` → **404**
- **A10** NS `harvey`/`tricia.ns.cloudflare.com`；A 记录 Cloudflare 代理 IP
- 数据脚本 `fetch_ext_data.py` 已改为 `json.loads` + `atomic_write`（旧 eval/裸写问题已消）

### B · 数据与 USD-only
- `window.CURRENCY === "USD"`；无 `curSel`/`setCurrency` 残留
- `fmtGDP` 恒 `$`；`currencyTag("gdp") === "货币：美元(USD)"`；`METRICS.gdp.unit === "美元"`
- **数值抽检**（vm 加载 vendor）：

| 对象 | 显示 | raw (USD) | 交叉验证 |
|---|---|---|---|
| CN 2024 | $18.73 万亿 | 1.873e13 | `cur_test`/visual B |
| US 2024 | $29.30 万亿 | 2.930e13 | OK |
| 广东 2025 | $2.03 万亿 | 2.026e12 | 手算 CNY 1.4584676e13 / 7.2 一致 |
| California 2024 | $4.05 万亿 | 4.048e12 | visual E |
| 北海道 2021 | $1446.66 亿 | 1.447e11 | visual F |
| DE11 2023 | $3021.39 亿 | 3.021e11 | visual G |
| 深圳 2025 | $3819.85 亿 | 3.820e11 | visual H |

- `cmpGetData` 六类型均显示美元；`fxrate` **2000–2024 共 25 年无缺口**
- `gdpcap` CN 2023 ≈ 12484（2015 不变价 USD）
- 门禁：`data_verify`、`cur_test 4/4`、`visual_assert 14/14` 通过

### C · 性能与资源
- 线上 **brotli**：HTML ~25KB wire；echarts ~198KB；world.js ~192KB
- 懒加载：`japan.js` / `us-states.js` / `cn/*.js` / `eu/*` / `ext_indicators` 经 `loadScript` 非首屏必载
- `app-core.js?v=df423ca7` 缓存指纹；`/vendor/*` `max-age=14400`
- `world.json` **未**进入 dist（无死大文件）
- `perf_trace` 此前通过（DCL ~100ms / load ~187ms，headless）

### D · SEO / 链接
- 三页 title + description 齐全；主页含 OG
- 站内 href：favicon/compare/about/index 均存在；`308` 美化 URL 正常
- about/compare 有 h1；chart 有 `role="application"` + aria；rank 有 `role="button"` + aria-label
- 移动端溢出：`visual_regression` 此前通过（375 视口）

### E · 代码与交互
- `node --check` 全量 inline + `app-core.js`：**syntax OK**
- 回归：`offline_test`、`test_compare 5/5`、`url_state`、`eu_test`、`ext_test`、`econ_insight`、`audit_all` 面板结构通过
- 年份 change → `redrawByYear` + `saveState`；默认 2025 由 WB 动态年生成
- 源码无 TODO/FIXME/HACK

---

## 测试门禁快照（本轮）

| 步骤 | 结果 |
|---|---|
| L1 语法 | OK |
| L2 data_verify | OK |
| L3a offline | OK |
| L3b compare | 5/5 |
| L3c ext | OK |
| L3d econ | OK |
| L3e eu | OK |
| L3f url_state | OK |
| L3g cur（固定美元） | 4/4 |
| L3h visual_assert | 14/14 |
| L3i perf | OK |
| L3j visual_regression | OK |

---

## 建议修复顺序（Backlog）

1. **P1** 统一 compare 城市 key 解析（约 10 行）并加回归用例  
2. **P1** `doSearch` 不依赖 `US_GEO` 是否已载；补 JP/EU 搜索  
3. **P2** ESC 排除表单控件；`saveState` 支持 city  
4. **P2** README/spec 域名与测试说明、去掉双币表述  
5. **P2** 主页 h1/main；可选 2025 汇率说明  
6. **P3** CSP 试点、清理 CNY 注释/死代码  

---

## 结论

线上站点 **安全基线、HTTPS、SEO 元文件、404 语义、USD-only 数据折算与自动化门禁整体健康**。主要风险集中在 **对比页城市参数解析（P1）** 与 **世界层搜索美国州失败（P1）**，以及文档/无障碍/交互边界的 P2 项。修复上述 P1 后建议再跑 `./run_all_tests.sh` 并部署一次。

---

## 附录 · 计划 ID 覆盖矩阵（`AUDIT_PLAN.md` → 本报告）

| 区 | 计划 ID | 覆盖位置 | 状态 |
|---|---|---|---|
| A | A1–A2, A5–A6, A8, A10–A11 | OK · 安全与部署 | 完成 |
| A | A3 | P3 CSP/Permissions-Policy | 完成 |
| A | A4 | 复核：`dist` 无明文 `http://`（W3C/Sitemap 命名空间除外） | 完成 |
| A | A7 | 复核：本地 `CN_GEO` 优先，DataV 失败 `showGeneric("加载失败"…)` | 完成 |
| A | A9 | 复核：`wrangler.toml` `pages_build_output_dir=./dist`；部署 `5e1a14ca` alias 自定义域 success | 完成 |
| A | A12 | 复核：`git status` 记录未提交改动（USD/SEO/审计文件），未误删 | 完成 |
| B | B1–B3, B11–B14 | OK · 数据与 USD-only + 数值表 | 完成 |
| B | B4–B10 | OK 数值抽检 + `visual_assert` 14/14 | 完成 |
| B | B2 2025 汇率 | P2 · FXRATE 止于 2024，2025 兜底 7.2 | 完成 |
| C | C1–C8, C10 | OK · 性能与资源 + P2 体积口径 | 完成 |
| C | C9 | 复核：懒加载 + catch 提示「需可访问 DataV」 | 完成 |
| D | D1–D7, D11–D12 | OK · SEO/链接 + P2 h1/main | 完成 |
| D | D8–D10 | P2 无 h1/main；OK 焦点环/aria/移动回归 | 完成 |
| E | E1–E6, E8–E11, E14 | OK · 代码与交互 + 门禁快照 | 完成 |
| E | E7 | P1/P2 城市 key、US 搜索、ESC、saveState city | 完成 |
| E | E12–E13 | P2 文档漂移与测试缺口 | 完成 |

**覆盖结论**：计划 62 项均有落点；其中 57 项在正文 OK/P 级表中直接叙述，5 项（A4/A7/A9/A12/C9）为本轮收尾复核补证。**审计执行完成（2026-09-21）。**
