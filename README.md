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

- 单 HTML 入口 + 本地 vendored 脚本（零构建，无打包步骤）：逻辑收敛在 `vendor/app-core.js`（~25KB），HTML 仅做 markup 并外链脚本与数据文件，离线 `file://` 可用
- 数据文件在 `vendor/`：World Bank（国家）、维基（中国省/市）、BEA（美国州）、日本内阁府（都道府县）、DataV GeoAtlas（中国边界）
- 懒加载：`vendor/japan.js` / `us-states.js` / `cn/{adcode}.js` / `ext_indicators.js` 按需或后台预加载，首屏同步约 2.4MB

## 测试（门禁）

```bash
./run_all_tests.sh    # 7/7：L1 语法 / L2 数据自洽（含欧盟）/ L3a 回归截图 / L3b 对比 / L3c 扩展指标 / L3d 四维洞察 / L3e 欧盟下钻
# 补充（按需）：tests/eu_edge_test.py 欧盟边界行为（指标守卫/年份/对比趋势/移动端）、tests/econ_insight_check.py 四维洞察
# 对比页专项：tests/test_compare.py（?add 参数 / 搜索添加 / 删除 / 轨迹图 / 层级点选）
# 面板结构盘点：tests/audit_all.py（各层仪表盘块 + 面板残留组件）
```

> 测试脚本统一放在 `tests/`；依赖 headless Chrome（`/Applications/Google Chrome.app`）。

## 数据构建（数据更新流程）

| 数据 | 脚本 | 说明 |
|---|---|---|
| 国家 GDP/人口/面积 + 扩展指标 | `fetch_wb_indicators.py` / `fetch_ext_data.py` / `fetch_ext_merge.py` | World Bank API，需出网 |
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

- 自定义域：`huajun.wang`（根域）+ `www.huajun.wang` 均 CNAME → `global-data-atlas.pages.dev`
- 配置：`wrangler.toml`（`pages_build_output_dir = "./dist"`）

## 文档

- `global-data-atlas-spec.md` — 需求规格 + DoD（验收标准）
- `global-data-atlas-v2-plan.md` — V2/V3 规划与决策记录
- `FEATURES.md` — 功能清单（当前状态，无规划项）
- `design-brief.md` — 视觉设计规范

## 已知限制

- 地图下钻依赖鼠标双击（ECharts canvas），**暂不支持键盘下钻**；键盘可操作范围：排行项 Enter/Space、ESC 返回、搜索 Enter
- 数据源为公开整理近似值，GDP 支持人民币/美元切换（逐年平均汇率折算），口径详见「关于」页
