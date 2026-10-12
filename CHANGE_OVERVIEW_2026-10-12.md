# Global Data Atlas · 变更总览（2026-10-12 会话）

- **对象**：`global-data-atlas`（GitHub `xy111a/global-data-atlas`，活跃副本 `WorkBuddy/2026-10-06…/global-data-atlas`）
- **线上**：https://atlas.huajun.wang（Cloudflare Pages，手动 `build.sh --deploy` 部署）
- **起点**：commit `3534505`；**终点**：commit `2ff566e`（=`origin/main`，工作区干净）
- **节奏**：每阶段固定 `build.sh 漂移校验 → run_all_tests.sh 门禁 → build.sh --deploy → tests/prod_probe.sh 线上复验 → git 提交单独确认`

---

## 一句话结论

由一次**多角度审计**发现「数据集刷新后陈旧缓存、部署对用户延迟生效」这一根问题，随后分阶段修根因、加指标、加洞察功能。本会话 **6 个提交全部上线并推 GitHub**；门禁从 **23 步扩到 24 步**、每步真实浏览器 + 线上探针复验通过；**无已知未修缺陷**。

---

## 本会话提交清单

| commit | 主题 | 一句话 |
|---|---|---|
| `679bcdf` | fix(cache)+audit (P1) | 数据刷新即时到达用户：全静态引用注 `?v`、`/vendor/*` max-age→0、SW `atlas-v2`、`?v` 归一 md5、新增线上探针 |
| `f1c32e8` | feat(B4)+data (P2) | 新增国家指标 **城镇化率 / 通胀率**（World Bank EXT，增量合并 + 6 断言） |
| `ea059e7` | feat(C2)+build(#4) (P2) | 动态资源也注 `?v`（`window.VHASH`）+ **全量数据导出 CSV/JSON**（+12 断言） |
| `bb655d2` | feat(P3·C1) | **Gapminder 关系散点**（echarts 加 `ScatterChart` 重建，门禁 23→24） |
| `f03e7f3` | feat(P3·C10) | compare.html **对比集分享链接**（复制 `?add`+指标+年份，入站还原） |
| `2ff566e` | fix(build) | frankfurter 汇率端点 `.app→.dev/v1`（修 301 永久迁移致 FX 静默回落基线的隐藏 bug） |

总计 29 文件、+1368 / −114 行。

---

## 核心问题与修复：数据刷新的缓存陈旧

**根因（审计发现）**：`_headers` 对 `/vendor/*` 设 `max-age=14400`（4h），但只有 `app-core.js`/`meta.js` 带 `?v=` 内容指纹；**数据集文件（如当天补全的 `us_pop_ts.js`）URL 恒定、内容变了 URL 没变** → 部署后边缘/浏览器最长 4h 仍供旧数据。当时线上实测：生产 `us_pop_ts.js` 还是旧稀疏序列（`cf-cache-status: HIT`），而部署的 dist 已是逐年 → 「修复上线了但用户看不到」。

**四层封堵（现已全部生效）**：
1. **`_headers`**：`/vendor/*` `max-age=14400 → 0, must-revalidate`（强制回源，未变走 304）。
2. **静态数据文件 `?v=`**：`build.sh` 通用注入器（Python `hashlib.md5`）给全部 14 个静态 `<script src>` 注 `?v=<md5前8>`（内容变→URL变→绕过边缘/浏览器/SW 三层）。
3. **动态文件 `window.VHASH`**：`build.sh` 内联 `dist/vendor/**/*.js` 的 79 个内容指纹，`loadScript()` / `loadCnProvGeo()` 运行时查表注 `?v` → `ext_indicators`、`japan`、`us-states`、`cn/eu 边界`（含动态拼接的 `vendor/eu/<cc>.js`）也能即时到达。
4. **Service Worker**：`CACHE` `atlas-v1→atlas-v2` 一次性清旧缓存；配合上面 `?v`，后续无需再 bump。

**验证**：线上取 `ext_indicators.js?v=…` 返回含 urban×182/inflation×164（新键即时到达）；`prod_probe.sh` 断言生产引用带 `?v` 且数据为逐年，全绿。

---

## 功能新增

- **指标（13→15 项）**：城镇化率（`SP.URB.TOTL.IN.ZS`，182 国）、通胀率（`FP.CPI.TOTL.ZG`，164 国）。经 METRICS 注册表接入，按钮自动生成、非国家层自动禁用。
- **全量导出**：工具栏「⬇ 全量CSV / ⬇ JSON」——当前层 × 当前指标 × 所有可得年份 的长表（CSV 带 UTF-8 BOM，JSON 含元信息），供二次分析。
- **关系散点（Gapminder）**：「🔵 散点」浮层——国家×当前年，X/Y 任意指标（默认 人均GDP↔预期寿命）、气泡=人口、长尾指标自动对数轴、跟随年份下拉重绘、ESC/点外关闭。
- **对比分享**：compare.html「🔗 分享」把当前对比集（区域+指标+年份）复制成 `?add=…` 链接；入站 `parseAddParam` 已能还原区域，新增回读 metric/year 以还原完整视图。

---

## 测试与门禁（保真度改进）

- 门禁 `run_all_tests.sh` **23 → 24 步**（新增 `scatter_test`）。
- 新增/扩充断言：`data_verify` +6（城镇化/通胀覆盖与方向、CN/US 锚点）；`export_test` 28/28（含全量导出 +12）；`test_compare` 11/11（含分享 +5）；`scatter_test` 9/9。
- **吸取 visualMap「配置存在≠渲染」教训**：散点测试断言 `getModel().getSeriesByType('scatter')===1` 且 `getData().count()≥100`（真渲染，不是只看 option）。
- **新机制 `prod_probe.sh`**：打生产 URL 断言「数据真的送到用户」，补「门禁只在本地跑、测不到部署→边缘→SW 分发链」这一元盲区。

---

## 取舍与未做（均有意，非遗漏）

- **C9 键盘下钻**：经核查已被现有 `drillBtn` + `drillCurrent()` + 排行项 Enter + 搜索覆盖，未重复实现。
- **日本 GDP→2023**：只读核实 ESRI `/2023/` 表存在，但对 石川·奈良·徳島·香川·宮崎 5 县 GDP 单元格为 `'-'`（缺值），合入会把日本覆盖从 47 降到 42、破坏完整性 → 依「缺就标 '—'、绝不编数据」原则放弃并回退。2024/2025 表目前 404。
- **城市序列自动刷新**：源为中文维基 wikitext 手工快照、无稳定 API、近年口径参差 → 不做。
- **P5**：用户明确**不做 CI 自动部署**（保持手动 `build.sh --deploy`）；D12 首屏瘦身 / i18n 为可选且不紧急。

---

## 当前状态

- GitHub `main` = `2ff566e`，工作区干净。
- Cloudflare Pages 生产：门禁 **24/24**、`prod_probe` 全绿、数据刷新缓存已四层封死。
- echarts 定制构建现含 `Line/Bar/Map/Scatter` + `Grid/Tooltip/Legend/Title/AxisPointer/DataZoom/VisualMap` + CanvasRenderer（642KB，含 ScatterChart）；构建管线经**逐字节可复现性**校验。

> 详细审计证据见同目录 `AUDIT_2026-10-12_multiangle.md`。
