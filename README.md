# 全球数据图谱 · Global Data Atlas

交互式全球行政区划数据地图（单页应用，桌面 + 移动端）。按行政层级下钻（世界 → 国家 → 中国省→地级市 / 美国州 / 日本都道府县），挂载公开经济数据（GDP/人口/面积 + 8 项扩展指标），支持指标切换、年份切换（2000–2025）、多区域对比、趋势洞察与增长排行。

线上：https://atlas.huajun.wang · https://global-data-atlas.pages.dev

## 快速开始

```bash
# 本地直接打开（完全离线，file:// 可用）
open global-data-atlas.html

# 或本地起服务
python3 -m http.server 8000   # 访问 http://localhost:8000
```

## 技术栈

- 单 HTML 入口 + 本地 vendored 脚本（零构建，无打包步骤）：逻辑收敛在 `vendor/app-core.js`（~40KB），HTML 仅做 markup 并外链脚本与数据文件，离线 `file://` 可用
- 图表库：`vendor/echarts.min.js` 为 Apache ECharts **5.6.1** 定制子集（Line/Bar/Map/Scatter + CanvasRenderer）；许可 banner 已保留
- 数据文件在 `vendor/`：World Bank（国家）、维基（中国省/市）、BEA（美国州）、日本内阁府（都道府县）、DataV GeoAtlas（中国边界）
- 首屏同步 JS 约 **1.65MB**（+ HTML ~130KB，压缩前；brotli 后约 550KB）；懒加载另计
- 懒加载：`vendor/japan.js` / `us-states.js` / `cn/{adcode}.js` / `eu/*` / `ext_indicators.js` 按需或后台预加载

## 测试（门禁）

```bash
./run_all_tests.sh    # 28 步：语法 / 数据自洽 / 增长口径 / meta 新鲜度 / 回归 / 对比 / 对比数据口径 / EXT / 四维洞察 / 欧盟 / URL / 深层URL / 固定美元 / 深度断言 / 性能 / 视觉回归 / 搜索ESC / 排行 / 配色 / 新鲜度 / SEO / 键盘 / 年份标签 / 顶栏 / 嵌入 / 欧盟多年 / 导出 / 散点
# 补充（按需）：tests/eu_edge_test.py 欧盟边界行为、tests/econ_insight_check.py 四维洞察
# 对比页专项：tests/test_compare.py（?add / 搜索添加 / 删除 / 轨迹图 / 层级点选 / 城市 key）
# 数据口径：tests/compare_data_test.py（NUTS 数值/城市名/年份）、tests/year_label_test.py（回退年标签）
# 分享链接：tests/url_restore_deep_test.py（level=province + city）
# 依赖：pip install -r tests/requirements.txt（Pillow + websocket-client，L3j 移动端真机模拟必需）
# 搜索/ESC：tests/search_esc_test.py
# 面板结构盘点：tests/audit_all.py（各层仪表盘块 + 面板残留组件）
```

> 测试脚本统一放在 `tests/`；依赖 headless Chrome（`/Applications/Google Chrome.app`）。

## 数据构建（数据更新流程）

| 数据 | 脚本 | 说明 |
|---|---|---|
| 国家 GDP/人口/面积 + 扩展指标 | `list_wb_indicators.py`（仅探索指标清单，不取数） / `fetch_ext_data.py` / `fetch_ext_merge.py` | World Bank API，需出网 |
| 中国省级序列 | `build_cn_prov.js` | 维基解析 |
| 中国城市序列/索引 | `build_city_ts.py`（依赖维基快照 `CITYGDP_WT`，默认 `/tmp/citygdp_wt.txt`，缺失时脚本会提示获取方式）/ `build_city_index.py`（本地，可复现） | |

> ⚠️ **数据更新注意事项**：`fetch_ext_data.py` / `fetch_ext_merge.py` 会**直接覆盖** `vendor/ext_indicators.js`，执行前先备份（脚本会打印警告）。
| 美国州 | `build_bea_states.js` | BEA API |
| 日本县 | `build_japan.py` | |
| 欧盟 NUTS2（EU27 全量） | `build_eu.py` | Eurostat GISCO 边界 + nama_10r_2gdp/demo_r_pjanaggr3 API + Frankfurter(ECB) 汇率；先下载边界 GeoJSON（脚本注释有命令） |
| 中文名同步 | `patch_cn_names.py` → `sync_cn_to_wb.py` | |

构建后需同步 `dist/`（`./build.sh` 一键同步 + md5 校验，或 `./build.sh --deploy` 直接上线）。

## 部署（Cloudflare Pages）

```bash
./build.sh --deploy   # 同步 source → dist + md5 校验 + 部署（推荐入口）
./build.sh            # 只同步 dist 并校验（防漂移门禁）

# 或手动部署（需先手动同步 dist）
cp global-data-atlas.html dist/ && cp global-data-atlas.html dist/index.html
env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy -u ALL_PROXY -u all_proxy \
  wrangler pages deploy dist --project-name=global-data-atlas --branch=main
```

- 自定义域：`atlas.huajun.wang` → Pages 项目 `global-data-atlas`（另有 `global-data-atlas.pages.dev`）
- 配置：`wrangler.toml`（`pages_build_output_dir = "./dist"`）
- 缓存：`pages.dev` 上 `/vendor/*` 为 `max-age=0, must-revalidate`；若自定义域仍是 4h，需在 Cloudflare 区域
  检查 Browser Cache TTL / Cache Rules 并改为 Respect Existing Headers（2026-10-24 实测自定义域被覆盖）

## 文档

- `global-data-atlas-spec.md` — 需求规格 + DoD（验收标准）
- `global-data-atlas-v2-plan.md` — V2/V3 规划与决策记录
- `FEATURES.md` — 功能清单（当前状态，无规划项）
- `design-brief.md` — 视觉设计规范

## 已知限制

- 地图本身（ECharts canvas）不支持键盘直接下钻；键盘路径为「排行/搜索选中 → 面板「下钻」按钮」，或 Enter/Space 激活排行项。ESC 返回上一级（表单控件与散点浮层除外）。
- 数据源为公开整理近似值，GDP 统一以美元（USD）计价，口径详见「关于」页
