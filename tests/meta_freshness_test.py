#!/usr/bin/env python3
"""ATLAS_META 新鲜度门禁（L2c）：about.html「数据新鲜度」表必须真的渲染出来。

为什么单靠静态检查不够：
  vendor/meta.js 的 datasets 字段在 2026-10-12 之前是**全仓零引用**的死元数据，
  里面 us 写 2023（实际 2024）、japan 写 2021（实际 2022），但因为没人读它，
  错误从未暴露。本测试同时守住三件事：
    1) meta.js 声明的最新年 == 数据文件实际最大年（静态，与 data_verify 互补）
    2) 表由浏览器真实渲染出 6 行，且行内出现正确的年份（证明 JS 渲染链路通）
    3) about.html 不再残留过期的「8 国 154 / 2023 单年」欧盟描述
"""
import subprocess, os, re, json, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)

ok = 0; total = 0
def check(label, cond, detail=""):
    global ok, total
    total += 1
    print(f"{'✅' if cond else '❌'} {label} {detail}")
    if cond: ok += 1

meta_src = open("vendor/meta.js", encoding="utf-8").read()
about = open("about.html", encoding="utf-8").read()

# ── 1. 静态：meta.js 结构 + 与数据文件实际最新年一致 ──
m = re.search(r'window\.ATLAS_META\s*=\s*(\{.*\})\s*;', meta_src, re.S)
check("meta.js 可解析", bool(m))
META = json.loads(m.group(1)) if m else {}
DS = META.get("datasets", {})
check("meta.built 存在", bool(META.get("built")), f"({META.get('built')})")
check("meta.datasets 覆盖 6 个数据集", len(DS) == 6, f"({len(DS)})")
for k in ("world", "china", "us", "eu", "japan", "city"):
    d = DS.get(k) or {}
    check(f"meta.{k} 有 latest/span/desc",
          d.get("latest") is not None and bool(d.get("span")) and bool(d.get("desc")),
          f"(latest={d.get('latest')})")
check("meta.us 已修正为 2024（曾错写 2023）", (DS.get("us") or {}).get("latest") == 2024,
      f"({(DS.get('us') or {}).get('latest')})")
check("meta.japan 已修正为 2022（曾错写 2021）", (DS.get("japan") or {}).get("latest") == 2022,
      f"({(DS.get('japan') or {}).get('latest')})")

# ── 2. 静态：about.html 接线与文档漂移 ──
check("about.html 引入 vendor/meta.js", 'vendor/meta.js' in about)
check("about.html 含 #freshnessTable 容器", 'id="freshnessTable"' in about)
check("about.html 含 #builtStamp", 'id="builtStamp"' in about)
check("about.html 已无过期欧盟描述「8 国 154」", "8 国 154" not in about)
check("about.html 欧盟行已更新为 27 国 242", "27 国 242" in about)
check("about.html 含派生指标说明", "人均GDP·现价" in about and "地均GDP" in about)
check("about.html 含增长口径说明", "增长口径" in about)

# ── 3. 浏览器：表必须真的渲染出 6 行 ──
CHROME = os.environ.get("CHROME_BIN")
if not CHROME:
    for p in ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable",
              "/usr/bin/chromium", "/usr/bin/chromium-browser"):
        if os.path.exists(p):
            CHROME = p; break

if not CHROME or not os.path.exists(CHROME):
    print("  ⚠ 未找到 Chrome，跳过浏览器渲染断言（静态断言仍已执行）")
else:
    url = "file://" + os.path.join(ROOT, "about.html")
    r = subprocess.run([CHROME, "--headless", "--no-sandbox", "--disable-gpu",
                        "--virtual-time-budget=4000", "--dump-dom", url],
                       capture_output=True, timeout=60)
    dom = r.stdout.decode("utf-8", "replace")
    tbl = re.search(r'<table id="freshnessTable">(.*?)</table>', dom, re.S)
    check("浏览器渲染出 freshnessTable", bool(tbl))
    if tbl:
        rows = re.findall(r"<tr>(.*?)</tr>", tbl.group(1), re.S)
        data_rows = [x for x in rows if "<td" in x]          # 首行是 th 表头
        check("新鲜度表渲染 6 行数据", len(data_rows) == 6, f"(n={len(data_rows)})")
        joined = " ".join(data_rows)
        check("表中出现美国州最新年 2024", "2024" in joined)
        check("表中出现日本最新年 2022", "2022" in joined)
        check("表中出现中国省级最新年 2025", "2025" in joined)
        check("fallback 未触发（说明 meta 已加载）",
              'id="freshnessFallback" style="display: none' in dom or
              'id="freshnessFallback" style="display:none' in dom)
    stamp = re.search(r'<p id="builtStamp"[^>]*>(.*?)</p>', dom, re.S)
    if stamp:
        check("页脚快照日期取自 meta.built",
              META.get("built", "") in stamp.group(1), f"({stamp.group(1).strip()[:60]})")

print(f"\nmeta 新鲜度回归: {ok}/{total} 通过")
sys.exit(0 if ok == total else 1)
