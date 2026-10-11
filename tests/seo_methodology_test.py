#!/usr/bin/env python3
"""T9 回归：可信度/SEO —— schema.org JSON-LD 结构化数据 + 方法论页 + sitemap/robots。
静态校验（无需浏览器）：{@graph 合法性、Dataset/WebApplication 必填字段、about 文档、
sitemap 覆盖站点地图、robots 声明}。JSON-LD 一旦写坏，搜索引擎静默失效，故纳入门禁。
"""
import json, re, os

ok = 0; total = 0
def check(label, cond, detail=""):
    global ok, total
    total += 1
    print(f"{'✅' if cond else '❌'} {label} {detail}")
    if cond: ok += 1

root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
main = open(os.path.join(root, "global-data-atlas.html"), encoding="utf-8").read()
about = open(os.path.join(root, "about.html"), encoding="utf-8").read()
sitemap = open(os.path.join(root, "sitemap.xml"), encoding="utf-8").read()
robots = open(os.path.join(root, "robots.txt"), encoding="utf-8").read()

# 1. JSON-LD 存在且合法
blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', main, re.S)
check("存在 application/ld+json 块", len(blocks) >= 1, f"(n={len(blocks)})")

data = None
if blocks:
    try:
        data = json.loads(blocks[0])
        check("JSON-LD 可被解析（语法合法）", True, "")
    except Exception as e:
        check("JSON-LD 可被解析（语法合法）", False, f"({e})")

if data:
    graph = data.get("@graph") or []
    types = [n.get("@type") for n in graph]
    check("@graph 含 Dataset", "Dataset" in types, f"({types})")
    check("@graph 含 WebApplication", "WebApplication" in types, f"({types})")
    ds = next((n for n in graph if n.get("@type") == "Dataset"), None)
    app = next((n for n in graph if n.get("@type") == "WebApplication"), None)
    if ds:
        check("Dataset 含 temporalCoverage", bool(ds.get("temporalCoverage")), f"({ds.get('temporalCoverage')})")
        check("Dataset 含 spatialCoverage", bool(ds.get("spatialCoverage")), f"({ds.get('spatialCoverage')})")
        check("Dataset 声明免费可得", ds.get("isAccessibleForFree") is True, "")
        check("Dataset 列出数据来源组织", len(ds.get("sourceOrganization") or []) >= 3,
              f"(n={len(ds.get('sourceOrganization') or [])})")
    if app:
        fl = app.get("featureList") or []
        check("WebApplication featureList 覆盖核心功能", len(fl) >= 5, f"(n={len(fl)})")
        check("WebApplication 标注免费", (app.get("offers") or {}).get("price") == "0", "")

# 2. 方法论页（about.html）文档完整 + 与实现同步
check("about 页说明「名义增长」排行口径", "名义增长" in about and "排行" in about, "")
check("about 页说明「对数刻度」配色", "对数" in about and "配色" in about or "对数刻度" in about, "")
check("about 页说明 ≈ 年份回退标注", "≈" in about and "回退" in about or "≈年份" in about, "")
check("about 数据源表已更新日本多年序列(2011–2022)", "2011" in about and "2022" in about, "")
check("about 数据源表已更新美国人口(2025 估算)", "2025 估算" in about, "")
check("about 页保留数据来源链接", "World Bank" in about and "Eurostat" in about, "")

# 3. sitemap / robots
check("sitemap 覆盖首页", "https://atlas.huajun.wang/</loc>" in sitemap or "<loc>https://atlas.huajun.wang/</loc>" in sitemap, "")
check("sitemap 覆盖 about 页", "/about</loc>" in sitemap, "")
check("sitemap 覆盖 compare 页", "/compare</loc>" in sitemap, "")
check("robots 声明 Sitemap", "Sitemap:" in robots, "")

print(f"\n可信度/SEO(T9)回归: {ok}/{total} 通过")
exit(0 if ok == total else 1)
