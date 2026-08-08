#!/usr/bin/env python3
"""清理回归专项：验证 CN 常量 gdp 移除后各面板正常"""
import subprocess, os, re

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

def make_variant(name, trigger_js):
    html = open("global-data-atlas.html", encoding="utf-8").read()
    inject = ("<script>window.addEventListener('load',function(){setTimeout(function(){"
              "try{" + trigger_js + "}catch(e){console.error('trigger',e);}},600);});</script>")
    html = html.replace("</body>", inject + "\n</body>")
    p = os.path.join("atlas_test", name)
    open(p, "w", encoding="utf-8").write(html)
    return "file://" + os.path.abspath(p)

def dump(url, wait=10):
    cmd = [CHROME, "--headless", "--no-sandbox", "--disable-gpu",
           f"--virtual-time-budget={wait*1000}", "--dump-dom", url]
    r = subprocess.run(cmd, capture_output=True, timeout=wait+15)
    return r.stdout.decode("utf-8", "replace")

# 1. 省级下钻标题（原 m.gdp → 现 cnGdpRMB）
dom = dump(make_variant("audit1.html",
    "loadChina();setTimeout(function(){loadProvince('浙江','330000')},1500)"), 15)
ok1 = "浙江 · 地级市" in dom and "GDP" in dom
print(f"1. 省级下钻标题: {'✅' if ok1 else '❌'}")

# 2. 省份面板（原 m.gdp 兜底 → 现 gd 直接）
dom2 = dump(make_variant("audit2.html", "showProvincePanel('四川')"), 10)
ok2 = "GDP (2023)" in dom2 and "四川" in dom2 and "6.14 万亿" in dom2
print(f"2. 省份面板: {'✅' if ok2 else '❌'}")

# 3. 中国层着色（原 m.gdp → cnGdpRMB）
dom3 = dump(make_variant("audit3.html", "loadChina()"), 10)
ok3 = "四川" in dom3 and "cnGdpRMB" not in dom3.split("</script>")[0]
print(f"3. 中国层加载: {'✅' if ok3 else '❌'}")
