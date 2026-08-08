#!/usr/bin/env python3
"""Phase C 验证：数据来源标签是否在各面板出现"""
import subprocess, os

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

cases = [
    ("国家(wb)", make_variant("c1.html", "showCountry(COUNTRIES.find(c=>c[2]==='US'))"), "World Bank"),
    ("省(wiki)", make_variant("c2.html", "showProvincePanel('广东')"), "维基百科"),
    ("州(bea)", make_variant("c3.html", "loadUS();setTimeout(function(){showUSStatePanel('California')},1200)"), "BEA"),
]
for label, url, expect in cases:
    dom = dump(url, 13)
    print(f"{label}: 来源标签={'是' if expect in dom else '否'} (期望 {expect})")
