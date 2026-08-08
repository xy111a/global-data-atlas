#!/usr/bin/env python3
"""V2 洞察功能验证：生成带触发脚本的测试变体并 headless 截图"""
import subprocess, os, sys

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SRC = "global-data-atlas.html"
OUT = "atlas_test"
os.makedirs(OUT, exist_ok=True)

def make_variant(name, trigger_js):
    html = open(SRC, encoding="utf-8").read()
    inject = ("<script>window.addEventListener('load',function(){setTimeout(function(){"
              "try{" + trigger_js + "}catch(e){console.error('trigger',e);}},600);});</script>")
    html = html.replace("</body>", inject + "\n</body>")
    p = os.path.join(OUT, name)
    open(p, "w", encoding="utf-8").write(html)
    return "file://" + os.path.abspath(p)

def shot(name, url, wait=11):
    path = os.path.join(OUT, name)
    cmd = [CHROME, "--headless", "--no-sandbox", "--disable-gpu",
           "--hide-scrollbars", "--window-size=1280,800",
           f"--virtual-time-budget={wait*1000}", f"--screenshot={path}", url]
    subprocess.run(cmd, capture_output=True, timeout=wait+15)
    sz = os.path.getsize(path) if os.path.exists(path) else 0
    print(f"  {'OK ' if sz>50000 else 'FAIL'} {name}: {sz}b")
    return sz

print("=== V2 洞察功能验证 ===\n")
# 1. 世界层：默认加载，应显示增长对比条形图
shot("v2_world_trend.png", "file://" + os.path.abspath(SRC), wait=9)
# 2. 中国省详情：广东 GDP 趋势折线
shot("v2_gd.png", make_variant("v2_gd.html",
    "loadChina();setTimeout(function(){showProvincePanel('广东')},1500)"), wait=13)
# 3. 美国州详情：California GDP 趋势折线
shot("v2_us.png", make_variant("v2_us.html",
    "loadUS();setTimeout(function(){showUSStatePanel('California')},1500)"), wait=13)
# 4. 中国层：各省增长对比
shot("v2_china_comp.png", make_variant("v2_china_comp.html", "loadChina()"), wait=12)
