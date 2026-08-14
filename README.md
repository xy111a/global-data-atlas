# 全球数据图谱 · Global Data Atlas

交互式全球行政区划数据地图（单页应用，桌面 + 移动端）。按行政层级下钻（世界 → 国家 → 中国省→地级市 / 美国州 / 日本都道府县），挂载公开经济数据（GDP/人口/面积 + 8 项扩展指标），支持指标切换、年份切换（2000–2025）、多区域对比、趋势洞察与增长排行。

线上：https://global-data-atlas.pages.dev · https://huajun.wang

## 快速开始

```bash
# 本地直接打开（完全离线，file:// 可用）
open global-data-atlas.html

# 或本地起服务
python3 -m http.server 8000   # 访问 http://localhost:8000
```

## 技术栈

- 单文件 HTML（零构建，内联 CSS/JS，~100KB 逻辑）+ ECharts 5 地图
- 数据文件在 `vendor/`：World Bank（国家）、维基（中国省/市）、BEA（美国州）、日本内阁府（都道府县）、DataV GeoAtlas（中国边界）
- 懒加载：`vendor/japan.js` / `us-states.js` / `cn/{adcode}.js` / `ext_indicators.js` 按需或后台预加载，首屏同步约 2.4MB

## 测试（门禁）

```bash
./run_all_tests.sh    # 6/6：L1 语法 / L2 数据自洽 / L3a 回归截图 / L3b 对比 / L3c 扩展指标 / L3d 四维洞察
```

## 数据构建（数据更新流程）

| 数据 | 脚本 | 说明 |
|---|---|---|
| 国家 GDP/人口/面积 + 扩展指标 | `fetch_wb_indicators.py` / `fetch_ext_data.py` / `fetch_ext_merge.py` | World Bank API，需出网 |
| 中国省级序列 | `build_cn_prov.js` | 维基解析 |
| 中国城市序列/索引 | `build_city_ts.py`（依赖维基快照）/ `build_city_index.py`（本地，可复现） | |
| 美国州 | `build_bea_states.js` | BEA API |
| 日本县 | `build_japan.py` | |
| 中文名同步 | `patch_cn_names.py` → `sync_cn_to_wb.py` | |

构建后需同步 `dist/`（`cp global-data-atlas.html dist/ && cp global-data-atlas.html dist/index.html`）。

## 部署（Cloudflare Pages）

```bash
# 绕过系统代理（本机代理会导致 fetch failed）
env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy -u ALL_PROXY -u all_proxy \
  npx wrangler pages deploy dist --project-name=global-data-atlas --branch=main
```

- 自定义域：`huajun.wang`（根域）+ `www.huajun.wang` 均 CNAME → `global-data-atlas.pages.dev`
- 配置：`wrangler.toml`（`pages_build_output_dir = "./dist"`）

## 文档

- `global-data-atlas-spec.md` — 需求规格 + DoD（验收标准）
- `global-data-atlas-v2-plan.md` — V2/V3 规划与决策记录
- `design-brief.md` — 视觉设计规范
