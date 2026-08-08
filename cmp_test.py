#!/usr/bin/env python3
"""对比模式功能验证：开启→点击多区域→检查对比框内容"""
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

# 1. 世界层对比：开模式 + 点美国 + 点日本
trigger = ("cmpMode=true;cmpRender();"
           "cmpHandleClick('country','美国','US');"
           "cmpHandleClick('country','日本','JP');cmpRender();")
dom = dump(make_variant("cmp1.html", trigger), 10)
# 提取 compareBox 内容
i=dom.find('compareBox'); box=dom[i:i+3000] if i>=0 else ""
ok1 = "美国" in box and "日本" in box and "对比" in box
ok2 = "万亿" in box  # GDP 格式化出现
print(f"1. 世界层对比: {'✅' if ok1 else '❌'} 美国+日本在对比框")
print(f"2. GDP 数值: {'✅' if ok2 else '❌'}")

# 2. 中国省份对比
trigger2 = ("loadChina();setTimeout(function(){"
            "cmpMode=true;cmpHandleClick('prov','广东','广东');"
            "cmpHandleClick('prov','浙江','浙江');cmpRender();},1200)")
dom2 = dump(make_variant("cmp2.html", trigger2), 13)
i=dom2.find('compareBox'); box2=dom2[i:i+3000] if i>=0 else ""
ok3 = "广东" in box2 and "浙江" in box2
print(f"3. 省份对比: {'✅' if ok3 else '❌'} 广东+浙江在对比框")

# 3. 美国州对比
trigger3 = ("loadUS();setTimeout(function(){"
            "cmpMode=true;cmpHandleClick('usstate','California','California');"
            "cmpHandleClick('usstate','Texas','Texas');cmpRender();},1200)")
dom3 = dump(make_variant("cmp3.html", trigger3), 13)
i=dom3.find('compareBox'); box3=dom3[i:i+3000] if i>=0 else ""
ok4 = "California" in box3 and "Texas" in box3
print(f"4. 州对比: {'✅' if ok4 else '❌'} California+Texas在对比框")
