#!/usr/bin/env python3
"""深层 URL 恢复回归（2026-10-24 审计）：
  #level=province&sel=city:440300:440000 必须同时恢复「广东地图 + 深圳市面板」。
  旧实现 LAYERS.province.render 未返回 Promise，sel 被随后的 loadChina() 覆盖。
"""
import subprocess, os, re, json

CHROME = os.environ.get("CHROME_BIN")
if not CHROME:
    for p in ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable",
              "/usr/bin/chromium", "/usr/bin/chromium-browser"):
        if os.path.exists(p):
            CHROME = p; break
assert CHROME and os.path.exists(CHROME), "未找到 Chrome/Chromium，请设 CHROME_BIN"
os.makedirs("atlas_test", exist_ok=True)

src = open("global-data-atlas.html", encoding="utf-8").read()
base = '<base href="file://%s/">' % os.path.abspath(".")
src = src.replace("</head>", base + "</head>", 1)
p = os.path.join("atlas_test", "url_restore_deep.html")
open(p, "w", encoding="utf-8").write(src)

url = "file://" + os.path.abspath(p) + "?x=1#level=province&sel=city:440300:440000&year=2025"
cmd = [CHROME, "--headless", "--no-sandbox", "--disable-gpu",
       "--virtual-time-budget=25000", "--dump-dom", url]
r = subprocess.run(cmd, capture_output=True, timeout=70)
dom = r.stdout.decode("utf-8", "replace")

checks = [
    ("面板标题为深圳市", "深圳市" in re.sub(r"<script.*?</script>", "", dom, flags=re.S)),
    ("省份上下文为广东", "广东" in re.search(r'id="crumb"[^>]*>(.*?)</h1>', dom, re.S).group(1) if re.search(r'id="crumb"[^>]*>(.*?)</h1>', dom, re.S) else False),
    ("城市指标块已渲染", "GDP (≈2023)" in dom),
]
ok = sum(1 for _, c in checks if c)
for label, c in checks:
    print(f"{'✅' if c else '❌'} {label}")
print(f"\n深层 URL 恢复: {ok}/{len(checks)} 通过")
raise SystemExit(0 if ok == len(checks) else 1)
