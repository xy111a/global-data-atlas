# Global Data Atlas · 全面审计计划

- **对象**：`/Users/huajun/WorkBuddy/2026-08-18-22-48-41/global-data-atlas`  
- **线上**：https://atlas.huajun.wang · Cloudflare Pages 项目 `global-data-atlas`  
- **基线**：git `fc92b57` + 本地未提交改动（去货币切换 / SEO·404 修复），已部署 `5e1a14ca`  
- **日期**：2026-09-21  
- **方法**：静态审查 + 脚本化探针 + 既有测试门禁 + 线上 HTTP/头/资源核查 + 关键路径 headless 断言  
- **分级**：P1 阻断/错误数据 · P2 明显缺陷/风险 · P3 改进项 · OK 已验证通过  

---

## 0. 审计范围与出范围

| 在范围内 | 出范围 |
|---|---|
| 源码（HTML/JS/vendor）与 dist 一致性 | 破坏性压测 / DDoS |
| 部署配置（Pages / _headers / DNS·TLS 抽检） | 账号级渗透（Cloudflare 控制台越权） |
| 数据口径与 USD-only 折算 | 重新抓取全量 World Bank/BEA 原始数据做全库 diff |
| 线上可用性、SEO、可访问性、性能 | 商业/法务合规意见 |
| 交互回归（主图/下钻/对比/URL 状态） | 第三方 DataV 边界服务 SLA |

---

## 1. 维度 A · 安全与部署配置（A1–A12）

| ID | 检查项 | 方法 | 通过标准 |
|---|---|---|---|
| A1 | HTTPS / HSTS | `curl -I` + 证书链 | TLS 有效；HSTS 含 preload（自定义域） |
| A2 | 安全响应头 | `_headers` + 线上响应 | nosniff、Referrer-Policy、X-Frame-Options |
| A3 | CSP / 权限策略 | 响应头 | 记录现状（有则列，无则 P3 建议） |
| A4 | 混合内容 / 外链协议 | 扫描 `http://`、第三方 URL | 全站 https 或明确可降级例外 |
| A5 | 敏感信息泄漏 | 源码/部署/测试产物 | 无 API key、token、内网路径进 dist |
| A6 | XSS 面 | `innerHTML`/`insertAdjacentHTML`/`esc()` 使用点 | 用户可控输入均转义或非用户输入 |
| A7 | 外部资源信任边界 | DataV fetch、CDN | 有失败兜底；不 eval 远程字符串 |
| A8 | dist 与 source 防漂移 | `./build.sh` md5 | 全部一致 |
| A9 | Pages 配置 | wrangler/API | 生产分支、域名 alias、无 Functions 误配 |
| A10 | DNS / TLS 抽检 | dig + openssl | NS、proxied IP、证书有效期 |
| A11 | robots/sitemap/404 | 线上 HTTP | 真实类型/状态码，非伪 200 HTML |
| A12 | Git 工作区卫生 | `git status` | 记录未提交改动；不误删 |

**产出**：A 区 findings 列表 + 头矩阵。

---

## 2. 维度 B · 数据正确性与 USD-only（B1–B14）

| ID | 检查项 | 方法 | 通过标准 |
|---|---|---|---|
| B1 | `CURRENCY` 恒为 USD | 源码 + headless | `window.CURRENCY==="USD"` |
| B2 | 无货币切换 UI 残留 | grep + DOM | 无 `curSel`/`setCurrency` |
| B3 | `fmtGDP` 恒 `$` | 单元/断言 | 无 `¥` GDP 展示 |
| B4 | 国家层（WB USD） | `visual_assert` B | 面板值 = `fmtGDP(regGet(...))` |
| B5 | 美国州（BEA USD） | visual_assert E | USD 量级，无 CNY 反模式 |
| B6 | 中国省（CNY→USD） | visual_assert D + 手算抽检 | 与 `gdpApply(cny,y)` 一致 |
| B7 | 中国市（CNY→USD + 序列） | visual_assert H | 序列年/回退年诚实 |
| B8 | 日本（JPY→CNY→USD 近似） | visual_assert F | 量级合理 + 近似披露 |
| B9 | 欧盟（EUR→CNY→USD） | visual_assert G | 与 EU_RATE 路径一致 |
| B10 | 趋势序列币种 | `provTrend`/`countryTrend`/`usTrend` | 均经 `gdpApply` |
| B11 | 对比页 `cmpGetData` | 源码 + compare 测试 | 各类型均折算到显示币种 |
| B12 | 人均 GDP / EXT | ext_test | gdpcap 仍为 USD 不变价 |
| B13 | 既有数据自洽门禁 | `data_verify.py` | 量级/范围通过 |
| B14 | 汇率表完整性 | `fxrate.js` 年覆盖 | 2000–2024 无空洞（2025 兜底） |

**产出**：B 区数值抽检表（原始值 / 汇率 / 展示值）。

---

## 3. 维度 C · 性能与资源（C1–C10）

| ID | 检查项 | 方法 | 通过标准 |
|---|---|---|---|
| C1 | 首屏 HTML 体积 | `curl` size | 记录；异常膨胀为 P3 |
| C2 | 关键 JS/CSS 体积 | vendor 清单 | echarts/world 等大文件可接受或有懒加载 |
| C3 | 首屏同步脚本数/字节 | 解析 script 标签 | 与 README「首屏 ~2.4MB」核对 |
| C4 | 懒加载路径 | japan/us/cn/ext | 按需或后台预载，不阻塞首屏 |
| C5 | 缓存头 | `_headers` + 响应 | vendor 4h；HTML must-revalidate |
| C6 | 缓存指纹 | `app-core.js?v=` | 构建注入，变更即失效 |
| C7 | gzip/br | `Content-Encoding` | 静态资源被压缩 |
| C8 | 运行时性能 | `perf_trace.py` | DCL/load 合理；无明显泄漏 |
| C9 | 外链 DataV | 失败路径 | 本地边界优先 / 有错误提示 |
| C10 | 重复/死资源 | dist 清单 | 无明显未引用大文件（记录即可） |

---

## 4. 维度 D · SEO / 可访问性 / 链接（D1–D12）

| ID | 检查项 | 方法 | 通过标准 |
|---|---|---|---|
| D1 | title / description / OG | 线上 HTML | 三页齐全、不重复空洞 |
| D2 | robots.txt | HTTP | `text/plain`，允许抓取、含 Sitemap |
| D3 | sitemap.xml | HTTP | `application/xml`，URL 可达 |
| D4 | favicon | HTTP | svg/ico 200 |
| D5 | 404 语义 | 不存在路径 | **404** 非 200 伪首页 |
| D6 | 美化 URL | `/about` `/compare` | 200 且内容正确 |
| D7 | 站内链接 | 解析 href | 无死链（相对路径） |
| D8 | 语义结构 | 标题层级 / landmarks | h1、header/main/footer 合理 |
| D9 | 键盘可达 | 已知限制核对 | 记录：双击下钻无键盘等 |
| D10 | 对比度/焦点 | 设计令牌抽查 | `:focus-visible`、muted 对比 |
| D11 | 移动端溢出 | visual_regression | scrollW ≤ innerW |
| D12 | aria 标签 | 关键控件 | search/year/chart 有 aria |

---

## 5. 维度 E · 代码质量与交互回归（E1–E14）

| ID | 检查项 | 方法 | 通过标准 |
|---|---|---|---|
| E1 | JS 语法 | `node --check` 全量 inline + app-core | 0 error |
| E2 | 语法门禁 L1 | `run_all_tests.sh` 相关步骤 | 通过 |
| E3 | 主路径：世界→CN→省→市 | visual_assert / offline | 面板+canvas |
| E4 | US/JP/EU 下钻 | visual_assert / eu_test | 通过 |
| E5 | 指标切换 11 项 | ext_test / 手测 | 不崩溃、守卫正确 |
| E6 | 年份切换 2025/2024/2023 | url_state + 面板 | 重绘+URL |
| E7 | 搜索 / 返回 / ESC | 交互逻辑审查 | 行为符合注释 |
| E8 | 对比页全路径 | test_compare | 5/5 |
| E9 | URL 状态持久化 | url_state_test | save/restore |
| E10 | 空态/错误态 | 缺数据边界 | “—”/提示，不抛未捕获异常 |
| E11 | 控制台错误 | headless 注入 | 无未捕获异常 |
| E12 | 文档一致性 | README/spec vs 行为 | USD-only、测试计数、域名 |
| E13 | 测试覆盖缺口 | 测试清单 vs 功能 | 列出未覆盖项 |
| E14 | 残留/TODO/FIXME | grep | 记录技术债 |

---

## 6. 执行顺序

1. **计划定稿**（本文件）→ T5 done  
2. **并行执行**  
   - A 安全部署（线上头/DNS/TLS/泄漏/XSS 面）  
   - B 数据与币种（源码路径 + 数值抽检）  
   - C 性能资源（体积/压缩/懒加载）  
   - D SEO/a11y/链接（线上探针）  
   - E 代码与回归（门禁全量 + 控制台）  
3. **交叉复核**：P1/P2 必须有可复现证据（命令输出或断言片段）  
4. **汇总报告**：按 P1→P3 + OK 清单 + 修复 backlog  

---

## 7. 验收标准（计划本身）

- [x] 覆盖安全、数据、性能、SEO/a11y、质量回归五大类  
- [x] 每项有方法与通过标准  
- [x] 与当前「仅美元」变更对齐（B 区强制）  
- [x] 线上与本地双侧验证  
- [x] 审计执行完毕并产出报告（`AUDIT_REPORT.md`，2026-09-21）  
